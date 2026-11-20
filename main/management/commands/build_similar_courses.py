"""
Build (or preview) similar-course recommendations.

    # Rebuild and save everything (run after importing/updating courses):
    python manage.py build_similar_courses

    # Tune without touching the database: print matches for a few courses.
    python manage.py build_similar_courses --preview "COMPSCI 351" "PSYCH 101"

    # Same, for 5 random courses (use --seed to get the same 5 each time):
    python manage.py build_similar_courses --sample 5 --seed 42

    # Try a setting change for one run (any key from DEFAULT_SETTINGS):
    python manage.py build_similar_courses --preview "COMPSCI 351" --set title_weight=3 --set min_score=0.2

Once a --set value looks better, copy it into DEFAULT_SETTINGS in
main/similarity.py and run the command without --preview/--sample to save.
"""

import ast
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from main.models import Course, SimilarCourse
from main.similarity import DEFAULT_SETTINGS, compute_similar_courses, normalize_code


class Command(BaseCommand):
    help = "Compute similar courses from titles/descriptions and save them."

    def add_arguments(self, parser):
        parser.add_argument("--preview", nargs="+", metavar="CODE",
                            help="Print matches for these course codes; nothing is saved.")
        parser.add_argument("--sample", type=int, metavar="N",
                            help="Print matches for N random courses; nothing is saved.")
        parser.add_argument("--seed", type=int, default=None,
                            help="Random seed for --sample so runs are comparable.")
        parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                            help="Override a setting for this run, e.g. --set title_weight=3")

    def handle(self, *args, **options):
        overrides = self.parse_overrides(options["set"])
        courses = list(Course.objects.values_list(
            "id", "course_code", "course_name", "course_details"))
        if not courses:
            raise CommandError("No courses in the database. Import courses first.")

        results, stats = compute_similar_courses(courses, overrides)
        self.stdout.write(
            f"Used {stats['courses_used']}/{stats['courses_total']} courses, "
            f"{stats['courses_with_matches']} got matches, "
            f"vocabulary {stats['vocabulary_size']} terms, "
            f"{stats['total_seconds']}s "
            f"(vectorize {stats['vectorize_seconds']}s + similarity {stats['similarity_seconds']}s)"
        )

        by_id = {c[0]: c for c in courses}
        if options["preview"] or options["sample"]:
            self.print_preview(courses, by_id, results, options)
            return

        rows = [
            SimilarCourse(course_id=course_id, similar_course_id=similar_id,
                          score=score, rank=rank)
            for course_id, matches in results.items()
            for rank, (similar_id, score) in enumerate(matches, start=1)
        ]
        with transaction.atomic():
            SimilarCourse.objects.all().delete()
            SimilarCourse.objects.bulk_create(rows, batch_size=2000)
        self.stdout.write(self.style.SUCCESS(f"Saved {len(rows)} similar-course links."))

    def parse_overrides(self, pairs):
        overrides = {}
        for pair in pairs:
            key, sep, raw = pair.partition("=")
            key = key.strip()
            if not sep or key not in DEFAULT_SETTINGS:
                raise CommandError(
                    f"Bad --set '{pair}'. Use KEY=VALUE with one of: {', '.join(DEFAULT_SETTINGS)}")
            try:
                value = ast.literal_eval(raw.strip())  # 3, 0.2, True, (1, 2), ["a", "b"]
            except (ValueError, SyntaxError):
                value = raw.strip()
            overrides[key] = value
        return overrides

    def print_preview(self, courses, by_id, results, options):
        if options["preview"]:
            wanted = {normalize_code(code) for code in options["preview"]}
            targets = [c for c in courses if normalize_code(c[1]) in wanted]
            missing = wanted - {normalize_code(c[1]) for c in targets}
            for code in sorted(missing):
                self.stdout.write(self.style.WARNING(f"\nNot found: {code}"))
        else:
            rng = random.Random(options["seed"])
            targets = rng.sample(courses, min(options["sample"], len(courses)))

        for course_id, code, title, _ in targets:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{normalize_code(code)} - {title}"))
            matches = results.get(course_id)
            if not matches:
                self.stdout.write("  (no matches - placeholder course or nothing above min_score)")
                continue
            for similar_id, score in matches:
                _, s_code, s_title, _ = by_id[similar_id]
                self.stdout.write(f"  {score:.2f}  {normalize_code(s_code)} - {s_title}")
