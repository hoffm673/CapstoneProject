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

    def test_registration_rejects_usernames_outside_character_limits(self):
        for username in ('ab', 'a' * 21):
            with self.subTest(username=username):
                response = self.client.post(reverse('register'), {
                    'username': username,
                    'email': 'student@uwm.edu',
                    'password': 'SecurePass123!',
                    'password_confirm': 'SecurePass123!',
                })

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Username must be 3-20 characters')
                self.assertFalse(User.objects.filter(username=username).exists())

    def test_registration_rejects_passwords_missing_required_character_types(self):
        passwords = (
            'Short1!',
            'lowercase1!',
            'UPPERCASE1!',
            'NoNumber!!',
            'NoSpecial123',
        )

        for password in passwords:
            with self.subTest(password=password):
                response = self.client.post(reverse('register'), {
                    'username': 'newstudent',
                    'email': 'student@uwm.edu',
                    'password': password,
                    'password_confirm': password,
                })

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Password must be at least 8 characters')
                self.assertFalse(User.objects.filter(username='newstudent').exists())


class ReviewSubmissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!"
        )
        self.professor = Professor.objects.create(professor_name="John Smith")
        self.course = Course.objects.create(
            course_name="Introduction to Computer Science",
            course_code="COMP SCI 101",
            course_credits=3
        )
        self.course.course_professors.add(self.professor)
        self.client.force_login(self.user)

    def valid_review_data(self):
        return {
            "course": self.course.id,
            "professor": self.professor.id,
            "difficulty_score": 4,
            "time_score": 5,
            "review_text": "This was a challenging but useful course.",
        }

    def test_successful_review_submission(self):
        response = self.client.post(
            reverse("review"),
            self.valid_review_data()
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

    def test_rejects_ratings_outside_range_or_not_integers(self):
        for field, value in (
            ("difficulty_score", "0"),
            ("difficulty_score", "6"),
            ("difficulty_score", "easy"),
            ("time_score", "-1"),
            ("time_score", "5.5"),
        ):
            with self.subTest(field=field, value=value):
                data = self.valid_review_data()
                data[field] = value
                response = self.client.post(reverse("review"), data)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Both ratings must be whole numbers")
                self.assertEqual(Review.objects.count(), 0)

    def test_rejects_blank_review_text(self):
        data = self.valid_review_data()
        data["review_text"] = " \n\t "
        response = self.client.post(reverse("review"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Review text cannot be blank")
        self.assertEqual(Review.objects.count(), 0)

    def test_rejects_professor_who_does_not_teach_course(self):
        other_professor = Professor.objects.create(professor_name="Dr. Other")
        data = self.valid_review_data()
        data["professor"] = other_professor.id
        response = self.client.post(reverse("review"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "professor who teaches the selected course")
        self.assertEqual(Review.objects.count(), 0)

    def test_rejects_invalid_course_or_professor_ids(self):
        for field in ("course", "professor"):
            with self.subTest(field=field):
                data = self.valid_review_data()
                data[field] = "invalid"
                response = self.client.post(reverse("review"), data)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Select a valid course and professor")
                self.assertEqual(Review.objects.count(), 0)
class ReviewInteractionTestBase(TestCase):
    """Shared setup: one review written by 'author', plus a second user 'reader'."""

    def setUp(self):
        self.author = User.objects.create_user(username='author', password='TestPass123!')
        self.reader = User.objects.create_user(username='reader', password='TestPass123!')
        professor = Professor.objects.create(professor_name='Dr. Test')
        course = Course.objects.create(
            course_code='COMP SCI 101', course_name='Intro', course_credits=3
        )
        course.course_professors.add(professor)
        self.review = Review.objects.create(
            review_user=self.author,
            review_course=course,
            review_professor=professor,
            difficulty_score=2,
            time_score=2,
            review_text='Good class.'
        )


class UpvoteTests(ReviewInteractionTestBase):

    def upvote(self):
        return self.client.post(reverse('toggle_upvote', args=[self.review.id]))

    def test_upvote_then_remove_upvote(self):
        self.client.force_login(self.reader)

        response = self.upvote()
        self.assertEqual(response.json(), {'upvoted': True, 'upvote_count': 1})

        response = self.upvote()
        self.assertEqual(response.json(), {'upvoted': False, 'upvote_count': 0})

    def test_each_user_counts_once(self):
        for user in (self.reader, self.author):
            self.client.force_login(user)
            self.upvote()

        self.assertEqual(self.review.review_upvotes.count(), 2)

    def test_logged_out_user_cannot_upvote(self):
        response = self.upvote()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.review.review_upvotes.count(), 0)

    def test_upvote_requires_post(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse('toggle_upvote', args=[self.review.id]))

        self.assertEqual(response.status_code, 405)

    def test_feed_shows_count_and_filled_heart(self):
        self.review.review_upvotes.add(self.reader)
        self.client.force_login(self.reader)

        response = self.client.get(reverse('review_page'))

        self.assertEqual(response.context['reviews'][0].upvote_count, 1)
        self.assertTrue(response.context['reviews'][0].user_upvoted)
        self.assertContains(response, 'bi-heart-fill')

    def test_feed_sorts_by_most_upvoted(self):
        other = Review.objects.create(
            review_user=self.reader,
            review_course=self.review.review_course,
            review_professor=self.review.review_professor,
            difficulty_score=3, time_score=3, review_text='Other review.'
        )
        other.review_upvotes.add(self.author, self.reader)

        response = self.client.get(reverse('review_page'), {'sort': 'top'})

        self.assertEqual(response.context['reviews'][0], other)


class CommentTests(ReviewInteractionTestBase):

    def add_comment(self, text):
        return self.client.post(
            reverse('add_comment', args=[self.review.id]),
            {'comment_text': text}
        )

    def load(self, offset=0):
        return self.client.get(
            reverse('review_comments', args=[self.review.id]),
            {'offset': offset}
        ).json()

    def test_add_comment(self):
        self.client.force_login(self.reader)
        response = self.add_comment('  Agreed, great class!  ')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['comment']['text'], 'Agreed, great class!')
        self.assertEqual(response.json()['comment_count'], 1)
        comment = Comment.objects.get()
        self.assertEqual(comment.comment_user, self.reader)
        self.assertEqual(comment.comment_review, self.review)

    def test_rejects_blank_and_too_long_comments(self):
        self.client.force_login(self.reader)

        for text in ('   ', 'x' * 1001):
            with self.subTest(length=len(text)):
                response = self.add_comment(text)
                self.assertEqual(response.status_code, 400)

        self.assertEqual(Comment.objects.count(), 0)

    def test_logged_out_user_cannot_comment(self):
        response = self.add_comment('Hello')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Comment.objects.count(), 0)

    def test_comments_load_three_at_a_time_oldest_first(self):
        for i in range(7):
            Comment.objects.create(
                comment_review=self.review, comment_user=self.reader, comment_text=f'Comment {i}'
            )

        first = self.load(0)
        second = self.load(3)
        third = self.load(6)

        self.assertEqual([c['text'] for c in first['comments']], ['Comment 0', 'Comment 1', 'Comment 2'])
        self.assertTrue(first['has_more'])
        self.assertEqual([c['text'] for c in second['comments']], ['Comment 3', 'Comment 4', 'Comment 5'])
        self.assertTrue(second['has_more'])
        self.assertEqual([c['text'] for c in third['comments']], ['Comment 6'])
        self.assertFalse(third['has_more'])

    def test_exactly_three_comments_has_no_show_more(self):
        for i in range(3):
            Comment.objects.create(
                comment_review=self.review, comment_user=self.reader, comment_text=f'Comment {i}'
            )

        self.assertFalse(self.load(0)['has_more'])

    def test_bad_offset_falls_back_to_start(self):
        Comment.objects.create(
            comment_review=self.review, comment_user=self.reader, comment_text='Only one'
        )

        self.assertEqual(self.load('abc')['comments'][0]['text'], 'Only one')

    def test_deleting_review_deletes_comments(self):
        Comment.objects.create(
            comment_review=self.review, comment_user=self.reader, comment_text='Bye'
        )
        self.review.delete()

        self.assertEqual(Comment.objects.count(), 0)

    def test_feed_shows_comment_count(self):
        Comment.objects.create(
            comment_review=self.review, comment_user=self.reader, comment_text='Hi'
        )
        self.review.review_upvotes.add(self.reader, self.author)

        response = self.client.get(reverse('review_page'))
        review = response.context['reviews'][0]

        # Both counts are correct together (guards against the join inflating either)
        self.assertEqual(review.comment_count, 1)
        self.assertEqual(review.upvote_count, 2)
