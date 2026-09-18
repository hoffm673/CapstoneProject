import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Capstone.settings')
django.setup()

# Take templates from models.py 
from main.models import Major, Professor, Course, Review, User




#
# File can be easily edited for various variables as needed to test parts of the website, for now all it
# will reasonably test is the recent reviews on the front page of our site since no other parts of the site really exist yet
#
def run_seed():
    print("--- Starting Database Seeding ---")

    # Majors of students
    majors_data = [
        "Computer Science",
        "Data Science",
        "Software Engineering",
    ]
    majors = {}
    for name in majors_data:
        major, created = Major.objects.get_or_create(major_name=name)
        majors[name] = major
        if created:
            print(f"Created Major: {name}")

    #Make fake professors
    professors_data = [
        "Dr. Joe",
        "Dr. Jane",
        "Dr. ABC",
    ]
    professors = {}
    for name in professors_data:
        prof, created = Professor.objects.get_or_create(professor_name=name)
        professors[name] = prof
        if created:
            print(f"Created Professor: {name}")

    # Creates a user with admin privleges and 4 normal users
    if not User.objects.filter(username="admin").exists():
        admin = User.objects.create_superuser(
            username="testadminuser",
            email="admin@uwm.edu",
            password="password",
            user_major=majors["Computer Science"]
        )
        print("Created Adminuser: testadminuser (password: password)")

    students_data = [
        ("alice", "alice@uwm.edu", majors["Computer Science"]),
        ("bob", "bob@uwm.edu", majors["Software Engineering"]),
        ("charlie", "charlie@uwm.edu", majors["Data Science"]),
        ("diana", "diana@uwm.edu", majors["Computer Science"]),
    ]

    users = {}
    for username, email, major in students_data:
        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.create_user(
                username=username,
                email=email,
                password="password",
                user_major=major
            )
            print(f"Created User: {username} (password: password)")
        users[username] = user

    # Create fake courses and assign professsors
    courses_data = [
        {
            "code": "COMP SCI 101",
            "name": "Introduction to CS",
            "credits": 3,
            "profs": ["Dr. Joe"]
        },
        {
            "code": "COMP SCI 200",
            "name": "Intermediate CS",
            "credits": 4,
            "profs": ["Dr. Joe", "Dr. Jane"]
        },
        {
            "code": "COMP SCI 351",
            "name": "Algorithm Design & Analysis",
            "credits": 3,
            "profs": ["Dr. ABC"]
        },
        {
            "code": "COMP SCI 400",
            "name": "CS 400",
            "credits": 3,
            "profs": ["Dr. ABC"]
        },
        {
            "code": "COMP SCI 506",
            "name": "CS 506",
            "credits": 3,
            "profs": ["Dr. Jane"]
        }
    ]

    courses = {}
    for c_data in courses_data:
        course, created = Course.objects.get_or_create(
            course_code=c_data["code"],
            defaults={
                "course_name": c_data["name"],
                "course_credits": c_data["credits"]
            }
        )
        if created:
            for p_name in c_data["profs"]:
                course.course_professors.add(professors[p_name])
            print(f"Created Course: {course.course_code} - {course.course_name}")
        courses[c_data["code"]] = course

    # Create fake reviews, follow format to add extra reviews as needed
    reviews_data = [
        {
            "user": users["alice"],
            "course": courses["COMP SCI 101"],
            "prof": professors["Dr. Joe"],
            "difficulty": 2,
            "time": 2,
            "text": "Great intro class! Explains basic concepts very clearly."
        },
        {
            "user": users["bob"],
            "course": courses["COMP SCI 351"],
            "prof": professors["Dr. ABC"],
            "difficulty": 5,
            "time": 5,
            "text": "Extremely challenging material, but you learn a lot!"
        }
    ]

    for r_data in reviews_data:
        # If script is run again we do not want to accidentally duplicate reviews
        existing_review = Review.objects.filter(
            review_user=r_data["user"],
            review_course=r_data["course"]
        ).first()

        if not existing_review:
            Review.objects.create(
                review_user=r_data["user"],
                review_course=r_data["course"],
                review_professor=r_data["prof"],
                difficulty_score=r_data["difficulty"],
                time_score=r_data["time"],
                review_text=r_data["text"]
            )
            print(f"Created Review for {r_data['course'].course_code} by {r_data['user'].username}")

    print("Fake reviews made")

if __name__ == "__main__":
    run_seed()