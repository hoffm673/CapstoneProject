import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count

from main.ai.gemini_client import GeminiCallFailed, GeminiNotConfigured
from main.ai.review_summary import generate_for_course, needs_refresh
from main.models import Course


class Command(BaseCommand):
    help = "Generate AI summaries of course reviews with Gemini"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--course")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        courses = (Course.objects.annotate(n=Count("review"))
                   .filter(n__gte=settings.AI_SUMMARY_MIN_REVIEWS).order_by("-n"))
        if opts["course"]:
            courses = courses.filter(course_code=opts["course"])

        todo = [c for c in courses if opts["all"] or needs_refresh(c)]
        if opts["limit"]:
            todo = todo[: opts["limit"]]
        self.stdout.write(f"{len(todo)} course(s) to summarize")

        if opts["dry_run"]:
            for c in todo:
                self.stdout.write(f"  would summarize {c.course_code} ({c.n} reviews)")
            return

        ok = failed = total_in = total_out = 0
        for i, course in enumerate(todo):
            try:
                obj = generate_for_course(course)
            except GeminiNotConfigured as exc:
                self.stderr.write(self.style.ERROR(str(exc)))
                return
            except GeminiCallFailed as exc:
                failed += 1
                self.stderr.write(self.style.WARNING(f"  {course.course_code}: {exc}"))
                continue
            if obj:
                ok += 1
                total_in += obj.input_tokens
                total_out += obj.output_tokens
                self.stdout.write(f"  {course.course_code}: ok "
                                  f"({obj.input_tokens} in / {obj.output_tokens} out)")
            if i < len(todo) - 1:
                time.sleep(settings.AI_SUMMARY_DELAY_SECONDS)

        self.stdout.write(self.style.SUCCESS(
            f"Done: {ok} ok, {failed} failed, {total_in} in, {total_out} out tokens"))