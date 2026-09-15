from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser

# Major model
class Major(models.Model):

    # Name of the major
    # Max name length = 100
    # Unique: Can't have multiple of the same major in the database
    major_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.major_name


# Professor model
class Professor(models.Model):
    professor_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.professor_name


# Course model
class Course(models.Model):

    # The name of the course (Ex. Algorithm Design & Analysis)
    course_name = models.CharField(max_length=100, unique=True)

    # The course code/identifier (Ex. COMP SCI 351)
    course_code = models.CharField(max_length=100, unique=True)

    # The number of credits the course is worth
    course_credits = models.IntegerField()

    # The selection of professors that teach the course
    # Uses ManyToManyField because a course can be taught by multiple professors/TAs
    course_professors = models.ManyToManyField(Professor)

    def __str__(self):
        return self.course_code + " - " + self.course_name


# Review model
class Review(models.Model):
    # Who the review is posted by
    # This is used to also see the reviewer's major
    review_user = models.ForeignKey("User",on_delete=models.CASCADE)

    # What course the review is for
    # Each review is referring to a single course
    review_course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)

    # The professor that was teaching the course being reviewed
    # Each review is referring to a single professor out of a list of options
    review_professor = models.ForeignKey(Professor, on_delete=models.SET_NULL, null=True)

    # The difficulty score that the review gives the course
    # 1 = The course material was extremely easy to understand
    # 5 = The course material was extremely complex and difficult to understand
    difficulty_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # The time consumption score that the review gives the course
    # 1 = Absolutely no time needs to be spent on this course outside of class
    # 5 = An insane amount of time needs to spend working on this course outside of class
    time_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # The review itself, the text that the reviewer types to talk about their experience in the course
    review_text = models.TextField()

    # The date the review was posted
    review_date = models.DateField(auto_now_add=True)


# User
# Imported AbstractUser from Django, it'll handle ID, username, password, & email
class User(AbstractUser):

    # The student's major
    # Can be left empty if the user has not selected a major
    # Deleting a Major will NOT delete users associated with that major
    user_major = models.ForeignKey(
        Major,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.username