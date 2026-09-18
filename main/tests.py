from django.test import TestCase
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
