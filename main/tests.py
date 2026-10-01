from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Course, Professor, Review, User


class CourseDetailTests(TestCase):
    """Tests for the course detail page and the search-page entry point."""

    def setUp(self):
        """Create a reusable course with one professor for each test."""
        self.professor = Professor.objects.create(professor_name='Dr. Test')
        self.course = Course.objects.create(
            course_code='COMP SCI 351',
            course_name='Algorithm Design and Analysis',
            course_credits=3
        )
        self.course.course_professors.add(self.professor)

    def test_course_detail_renders_course_information(self):
        """The detail page should show course metadata, stats, and review text."""
        user = User.objects.create_user(username='student', password='password')
        Review.objects.create(
            review_user=user,
            review_course=self.course,
            review_professor=self.professor,
            difficulty_score=4,
            time_score=3,
            review_text='Useful course with steady work.'
        )

        response = self.client.get(reverse('course_detail', args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COMP SCI 351')
        self.assertContains(response, 'Algorithm Design and Analysis')
        self.assertContains(response, 'Dr. Test')
        self.assertContains(response, '4.0 / 5')
        self.assertContains(response, 'Useful course with steady work.')

    def test_search_page_links_to_course_detail(self):
        """The course list should link each result to its detail page."""
        response = self.client.get(reverse('search'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse('course_detail', args=[self.course.id])
        )


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RegistrationTests(TestCase):
    """Tests for account creation and email verification setup."""

    def test_registration_sends_verification_email(self):
        response = self.client.post(reverse('register'), {
            'username': 'newstudent',
            'email': 'newstudent@uwm.edu',
            'password': 'A secure password 123!',
            'password_confirm': 'A secure password 123!',
        })

        user = User.objects.get(username='newstudent')
        self.assertRedirects(response, reverse('verify_email'))
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('verification code', mail.outbox[0].body)


class ReviewSubmissionTests(TestCase):
    # Set up the test data needed to submit a review
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword"
        )

        self.professor = Professor.objects.create(
            professor_name="John Smith"
        )

        self.course = Course.objects.create(
            course_name="Introduction to Computer Science",
            course_code="COMP SCI 101",
            course_credits=3
        )

        self.course.course_professors.add(self.professor)

    # Test that a user who is not logged in cannot submit a review
    def test_successful_review_submission(self):
        self.client.login(
            username="testuser",
            password="testpassword"
        )

        response = self.client.post(
            reverse("review"),
            {
                "course": self.course.id,
                "professor": self.professor.id,
                "difficulty_score": 4,
                "time_score": 5,
                "review_text": "This was a challenging but useful course."
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("search"))

        self.assertEqual(Review.objects.count(), 1)

        review = Review.objects.first()

        self.assertEqual(review.review_user, self.user)
        self.assertEqual(review.review_course, self.course)
        self.assertEqual(review.review_professor, self.professor)
        self.assertEqual(review.difficulty_score, 4)
        self.assertEqual(review.time_score, 5)
        self.assertEqual(
            review.review_text,
            "This was a challenging but useful course."
        )