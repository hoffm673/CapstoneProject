"""
Seed a labeled set of course reviews for building and testing review
summaries and aggregation.

Every review below carries hand-written labels describing what the TEXT says,
so you can check any summary/classification logic against a known answer:

    instructor : positive | negative | mixed | none   (none = instructor not mentioned)
    material   : easy | moderate | hard               (how difficult the content is)
    workload   : light | moderate | heavy             (time spent outside class)
    archetype  : the pattern the review was written to represent

Each course is written around a deliberate "story" so aggregates have signal:
    COMP SCI 101 / Dr. Joe   -> easy, light workload, well-liked instructor
    COMP SCI 200 / Dr. Joe   -> same course, strong instructor
    COMP SCI 200 / Dr. Jane  -> same course, weak instructor (compare by professor)
    COMP SCI 351 / Dr. ABC   -> hard material, heavy workload, "hard but fair"
    COMP SCI 400 / Dr. ABC   -> time consuming but NOT difficult (busywork)
    COMP SCI 506 / Dr. Jane  -> polarized / disorganized

It also includes a few edge cases: a review whose scores disagree with its text,
a one-line review, and informal slang.

Usage:
    python seed_reviews.py                     # add the labeled reviews
    python seed_reviews.py --reset             # delete them first, then re-add
    python seed_reviews.py --export labels.json  # write the labeled dataset to JSON (no DB changes)
"""
import argparse
import json
import os
from datetime import timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Capstone.settings')
django.setup()

from django.utils import timezone  # noqa: E402

from main.models import Course, Major, Professor, Review, User  # noqa: E402

REVIEWER_PREFIX = "reviewer"
REVIEWER_COUNT = 12
REVIEWER_PASSWORD = "Password123!"

MAJORS = [
    "Computer Science",
    "Data Science",
    "Software Engineering",
    "Mathematics",
    "Information Science & Technology",
]

COURSES = {
    "COMP SCI 101": {"name": "Introduction to CS", "credits": 3, "profs": ["Dr. Joe"]},
    "COMP SCI 200": {"name": "Intermediate CS", "credits": 4, "profs": ["Dr. Joe", "Dr. Jane"]},
    "COMP SCI 351": {"name": "Algorithm Design & Analysis", "credits": 3, "profs": ["Dr. ABC"]},
    "COMP SCI 400": {"name": "CS 400", "credits": 3, "profs": ["Dr. ABC"]},
    "COMP SCI 506": {"name": "CS 506", "credits": 3, "profs": ["Dr. Jane"]},
}


def r(course, prof, difficulty, time, text, instructor, material, workload, archetype):
    return {
        "course": course,
        "professor": prof,
        "difficulty_score": difficulty,
        "time_score": time,
        "review_text": text,
        "labels": {
            "instructor": instructor,
            "material": material,
            "workload": workload,
            "archetype": archetype,
        },
    }


REVIEWS = [
    # ---- COMP SCI 101 / Dr. Joe: easy, light, great instructor ----
    r("COMP SCI 101", "Dr. Joe", 1, 1,
      "Dr. Joe is one of the best lecturers I've had. He explains concepts slowly with lots of "
      "examples, and the homework takes maybe an hour a week.",
      "positive", "easy", "light", "easy_light_great_instructor"),
    r("COMP SCI 101", "Dr. Joe", 2, 2,
      "Very manageable intro course. Labs are short and Dr. Joe answers questions on the "
      "discussion board within a few hours.",
      "positive", "easy", "light", "easy_light_great_instructor"),
    r("COMP SCI 101", "Dr. Joe", 1, 2,
      "If you've programmed before you can coast. Lectures are clear but way too slow for me.",
      "mixed", "easy", "light", "easy_light"),
    r("COMP SCI 101", "Dr. Joe", 2, 1,
      "Easiest A I've gotten. Dr. Joe genuinely cares whether students understand and holds "
      "extra office hours before every exam.",
      "positive", "easy", "light", "easy_light_great_instructor"),
    r("COMP SCI 101", "Dr. Joe", 3, 2,
      "I had zero coding experience and the second half with loops and functions was tough for "
      "me, but Dr. Joe was patient with me in office hours.",
      "positive", "moderate", "light", "great_instructor"),
    r("COMP SCI 101", "Dr. Joe", 1, 1,
      "Fine class. Nothing memorable. Show up, do the labs, pass.",
      "none", "easy", "light", "neutral"),
    r("COMP SCI 101", "Dr. Joe", 2, 3,
      "Material is easy but the weekly quizzes add up. Dr. Joe's slides are great for studying.",
      "positive", "easy", "moderate", "great_instructor"),
    r("COMP SCI 101", "Dr. Joe", 1, 1,
      "ez class lol. joe is goated, just do the labs and ur good",
      "positive", "easy", "light", "informal_slang"),

    # ---- COMP SCI 200 / Dr. Joe: strong instructor ----
    r("COMP SCI 200", "Dr. Joe", 3, 3,
      "Dr. Joe made recursion actually click for me. Projects are a step up from 101 but very "
      "doable if you start early.",
      "positive", "moderate", "moderate", "great_instructor"),
    r("COMP SCI 200", "Dr. Joe", 3, 4,
      "Projects take a full weekend each, but the material itself is fair. Dr. Joe's lectures "
      "are organized and he posts recordings.",
      "positive", "moderate", "heavy", "great_instructor"),
    r("COMP SCI 200", "Dr. Joe", 2, 3,
      "Take this with Dr. Joe if you can. Clear expectations, fair grading, reasonable workload.",
      "positive", "easy", "moderate", "great_instructor"),
    r("COMP SCI 200", "Dr. Joe", 4, 3,
      "Harder than I expected, the data structures unit was rough. Dr. Joe was really helpful "
      "though.",
      "positive", "hard", "moderate", "great_instructor"),

    # ---- COMP SCI 200 / Dr. Jane: weak instructor ----
    r("COMP SCI 200", "Dr. Jane", 4, 4,
      "Dr. Jane reads straight off the slides and rarely takes questions. I learned more from "
      "YouTube than from lecture.",
      "negative", "hard", "heavy", "poor_instructor"),
    r("COMP SCI 200", "Dr. Jane", 4, 3,
      "The material honestly isn't that bad, the instructor just makes it confusing. Assignments "
      "were posted late with unclear instructions.",
      "negative", "moderate", "moderate", "score_text_mismatch"),
    r("COMP SCI 200", "Dr. Jane", 5, 4,
      "Grading felt random and feedback was nonexistent. Avoid Dr. Jane's section if you have "
      "the option.",
      "negative", "hard", "heavy", "poor_instructor"),
    r("COMP SCI 200", "Dr. Jane", 3, 3,
      "Dr. Jane clearly knows the material, she's just not great at explaining it. Office hours "
      "were more useful than lectures.",
      "mixed", "moderate", "moderate", "poor_instructor"),
    r("COMP SCI 200", "Dr. Jane", 4, 5,
      "Way too much work for a 4 credit class, and the lectures didn't prepare us for the "
      "projects at all.",
      "negative", "hard", "heavy", "poor_instructor"),

    # ---- COMP SCI 351 / Dr. ABC: hard material, heavy workload, fair instructor ----
    r("COMP SCI 351", "Dr. ABC", 5, 5,
      "Hardest class in the major, no question. Dr. ABC is brilliant and fair, but the proofs on "
      "the problem sets took me 15+ hours a week.",
      "positive", "hard", "heavy", "hard_but_fair"),
    r("COMP SCI 351", "Dr. ABC", 5, 4,
      "Brutal exams. Dr. ABC is clear in lecture, but the jump from lecture examples to the "
      "homework is huge.",
      "positive", "hard", "heavy", "hard_but_fair"),
    r("COMP SCI 351", "Dr. ABC", 4, 5,
      "Don't pair this with another heavy class. The problem sets are long. You will learn a "
      "ton though.",
      "none", "hard", "heavy", "hard_heavy"),
    r("COMP SCI 351", "Dr. ABC", 5, 5,
      "I struggled the entire semester. The pace is fast and Dr. ABC assumes you remember all of "
      "discrete math.",
      "negative", "hard", "heavy", "hard_heavy"),
    r("COMP SCI 351", "Dr. ABC", 4, 4,
      "Challenging but rewarding. Go to every TA session, they make all the difference.",
      "none", "hard", "heavy", "hard_but_fair"),
    r("COMP SCI 351", "Dr. ABC", 3, 4,
      "Honestly not as bad as everyone says if your math background is strong. Dr. ABC's notes "
      "are excellent.",
      "positive", "moderate", "heavy", "hard_but_fair"),
    r("COMP SCI 351", "Dr. ABC", 5, 5,
      "Worst semester of my life because of this course, but Dr. ABC was always willing to help "
      "in office hours.",
      "positive", "hard", "heavy", "hard_but_fair"),

    # ---- COMP SCI 400 / Dr. ABC: time consuming, NOT difficult ----
    r("COMP SCI 400", "Dr. ABC", 2, 5,
      "None of the concepts are hard, it's just an enormous amount of busywork. Weekly reports, "
      "peer reviews, and a semester-long project.",
      "none", "easy", "heavy", "time_consuming_not_difficult"),
    r("COMP SCI 400", "Dr. ABC", 2, 4,
      "Easy material, tons of hours. Budget at least 10 hours a week for the group project.",
      "none", "easy", "heavy", "time_consuming_not_difficult"),
    r("COMP SCI 400", "Dr. ABC", 1, 5,
      "Nothing in this class is conceptually difficult. The problem is the sheer volume of "
      "deliverables every single week.",
      "none", "easy", "heavy", "time_consuming_not_difficult"),
    r("COMP SCI 400", "Dr. ABC", 2, 5,
      "Dr. ABC is nice and the lectures are easy to follow, but the workload is way out of "
      "proportion for 3 credits.",
      "positive", "easy", "heavy", "time_consuming_not_difficult"),
    r("COMP SCI 400", "Dr. ABC", 3, 4,
      "Time sink. The documentation requirements on every assignment are excessive, and I "
      "learned little I didn't already know.",
      "none", "moderate", "heavy", "time_consuming_not_difficult"),
    r("COMP SCI 400", "Dr. ABC", 2, 4,
      "If you're organized and stay on top of deadlines it's a guaranteed good grade. Just very "
      "time consuming.",
      "none", "easy", "heavy", "time_consuming_not_difficult"),
    r("COMP SCI 400", "Dr. ABC", 1, 3,
      "Material is simple and the workload was fine once our group split tasks evenly.",
      "none", "easy", "moderate", "contrarian"),

    # ---- COMP SCI 506 / Dr. Jane: polarized / disorganized ----
    r("COMP SCI 506", "Dr. Jane", 3, 3,
      "Interesting topics but the course is disorganized. Deadlines changed twice without "
      "notice.",
      "negative", "moderate", "moderate", "disorganized"),
    r("COMP SCI 506", "Dr. Jane", 2, 2,
      "Honestly a pretty chill class. Dr. Jane is laid back and the final project is "
      "open-ended.",
      "positive", "easy", "light", "polarized"),
    r("COMP SCI 506", "Dr. Jane", 4, 4,
      "Dr. Jane never posted grades until the last week, so I had no idea where I stood. The "
      "material was challenging too.",
      "negative", "hard", "heavy", "disorganized"),
    r("COMP SCI 506", "Dr. Jane", 3, 2,
      "Light workload, but lectures wander off topic a lot. Fine if you're self-motivated.",
      "negative", "moderate", "light", "disorganized"),
    r("COMP SCI 506", "Dr. Jane", 2, 3,
      "Loved this class. Dr. Jane brings in real industry examples and is very approachable.",
      "positive", "easy", "moderate", "polarized"),
    r("COMP SCI 506", "Dr. Jane", 3, 3,
      "It's okay.",
      "none", "moderate", "moderate", "minimal_text"),
]


def ensure_catalog():
    majors = [Major.objects.get_or_create(major_name=name)[0] for name in MAJORS]

    professors = {}
    for info in COURSES.values():
        for name in info["profs"]:
            professors[name] = Professor.objects.get_or_create(professor_name=name)[0]

    courses = {}
    for code, info in COURSES.items():
        course, _ = Course.objects.get_or_create(
            course_code=code,
            defaults={"course_name": info["name"], "course_credits": info["credits"]},
        )
        for name in info["profs"]:
            course.course_professors.add(professors[name])  # no-op if already linked
        courses[code] = course

    return majors, professors, courses


def ensure_reviewers(majors):
    reviewers = []
    for i in range(1, REVIEWER_COUNT + 1):
        username = f"{REVIEWER_PREFIX}{i:02d}"
        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.create_user(
                username=username,
                email=f"{username}@uwm.edu",
                password=REVIEWER_PASSWORD,
                user_major=majors[i % len(majors)],
            )
        reviewers.append(user)
    return reviewers


def seed(reset=False):
    if reset:
        deleted, _ = Review.objects.filter(
            review_user__username__startswith=REVIEWER_PREFIX
        ).delete()
        print(f"Deleted {deleted} existing labeled reviews.")

    majors, professors, courses = ensure_catalog()
    reviewers = ensure_reviewers(majors)

    today = timezone.localdate()
    per_course_count = {}
    created = 0

    for i, data in enumerate(REVIEWS):
        course = courses[data["course"]]
        # Each reviewer reviews a given course at most once, like a real user would.
        n = per_course_count.get(data["course"], 0)
        per_course_count[data["course"]] = n + 1
        user = reviewers[n]

        if Review.objects.filter(review_user=user, review_course=course).exists():
            continue

        review = Review.objects.create(
            review_user=user,
            review_course=course,
            review_professor=professors[data["professor"]],
            difficulty_score=data["difficulty_score"],
            time_score=data["time_score"],
            review_text=data["review_text"],
        )
        # review_date is auto_now_add, so spread dates out afterwards
        # (roughly the last 5 months) to make date-based aggregation testable.
        Review.objects.filter(pk=review.pk).update(
            review_date=today - timedelta(days=(i * 11) % 150)
        )
        created += 1

    print(f"Created {created} labeled reviews ({len(REVIEWS) - created} already existed).")


def export(path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(REVIEWS, f, indent=2)
    print(f"Wrote {len(REVIEWS)} labeled reviews to {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="delete previously seeded labeled reviews first")
    parser.add_argument("--export", metavar="PATH", help="write the labeled dataset to a JSON file and exit")
    args = parser.parse_args()

    if args.export:
        export(args.export)
    else:
        seed(reset=args.reset)
