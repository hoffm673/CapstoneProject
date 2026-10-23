from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.db.models import Avg, Count
from .models import User
from .models import Review
from .models import Course, Professor
from django.core.mail import send_mail
import re
import random
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q, Case, When, Value, IntegerField
from .models import Course, Professor, Comment
from django.db.models import Exists, OuterRef
from django.views.decorators.http import require_GET, require_POST
from django.db.models import BooleanField



def home(request):
    """Render the home page with the two most recent course reviews."""
    # Pull related records in the same query so the template does not issue
    # extra database queries for each review card.
    recent_reviews = Review.objects.select_related(
        'review_course', 
        'review_professor', 
        'review_user__user_major'
    ).order_by('-review_date', '-id')[:2]

    return render(request, 'home.html', {
        'recent_reviews': recent_reviews
    })

@login_required
def review(request):
    """Render the review submission form with selectable courses and professors."""
    courses = Course.objects.all().order_by('course_code')
    professors = Professor.objects.all().order_by('professor_name')

    # Takes the inputs from the review form (POST) and adds them in the database
    if request.method == 'POST':
        course_id = request.POST.get('course')
        professor_id = request.POST.get('professor')
        difficulty_score = request.POST.get('difficulty_score')
        time_score = request.POST.get('time_score')
        review_text = request.POST.get('review_text', '').strip()

        try:
            course = Course.objects.get(pk=course_id)
            professor = Professor.objects.get(pk=professor_id)
        except (Course.DoesNotExist, Professor.DoesNotExist, TypeError, ValueError):
            return render(request, 'review.html', {
                'courses': courses,
                'professors': professors,
                'error': 'Select a valid course and professor.',
            })

        if not course.course_professors.filter(pk=professor.pk).exists():
            return render(request, 'review.html', {
                'courses': courses,
                'professors': professors,
                'error': 'Select a professor who teaches the selected course.',
            })

        try:
            difficulty_score = int(difficulty_score)
            time_score = int(time_score)
        except (TypeError, ValueError):
            difficulty_score = time_score = None

        if (
            difficulty_score not in range(1, 6)
            or time_score not in range(1, 6)
        ):
            return render(request, 'review.html', {
                'courses': courses,
                'professors': professors,
                'error': 'Both ratings must be whole numbers from 1 to 5.',
            })

        if not review_text:
            return render(request, 'review.html', {
                'courses': courses,
                'professors': professors,
                'error': 'Review text cannot be blank.',
            })

        # Creates a new Review object using the data collected from the form (POST)
        Review.objects.create(
            review_user=request.user,
            review_course=course,
            review_professor=professor,
            difficulty_score=difficulty_score,
            time_score=time_score,
            review_text=review_text
        )

        # Redirects the user to the 'search' page after submitting review
        return redirect('search')

    return render(request, 'review.html', {
        'courses': courses,
        'professors': professors,
    })

def logout_view(request):
    """Log the user out and redirect to the home page."""
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')

# Number of courses shown per page on the search page (pick anything in the 15-20 range)
COURSES_PER_PAGE = 20

def search(request):
    """Render a paginated course list, optionally filtered by a search query."""
    query = request.GET.get('query', '').strip()
    department = request.GET.get('department', '').strip()
    professor_id = request.GET.get('professor', '').strip()
    credits = request.GET.get('credits', '').strip()
    difficulty = request.GET.get('difficulty', '').strip()

    # Base queryset with annotations for average difficulty
    courses = Course.objects.prefetch_related('course_professors').annotate(
        avg_difficulty=Avg('review__difficulty_score')
    ).order_by('course_code')
    if query:
        courses = courses.filter(
            Q(course_code__icontains=query) |
            Q(course_name__icontains=query) |
            Q(course_professors__professor_name__icontains=query)
        ).distinct()

        # 2. Filter by Department (matching the prefix of course_code, e.g., "COMP SCI")
    if department:
        courses = courses.filter(course_code__icontains=department)

        # 3. Filter by Professor ID
    if professor_id:
        courses = courses.filter(course_professors__id=professor_id)

        # 4. Filter by Credits
    if credits:
        courses = courses.filter(course_credits=credits)

        # 5. Filter by Difficulty (matching the bucket range, e.g., 3.0 to < 4.0)
    if difficulty:
        diff_float = float(difficulty)
        courses = courses.filter(avg_difficulty__gte=diff_float, avg_difficulty__lt=diff_float + 1.0)

        courses = courses.distinct()
    paginator = Paginator(courses, COURSES_PER_PAGE)
    # get_page handles bad/out-of-range page numbers gracefully
    page_obj = paginator.get_page(request.GET.get('page'))

    # Shows something like: 1 ... 4 5 [6] 7 8 ... 20
    page_range = paginator.get_elided_page_range(
        page_obj.number, on_each_side=2, on_ends=1
    )

    # Data to populate dropdown filters in your HTML template
    professors = Professor.objects.all().order_by('professor_name')
    departments = sorted(
        list(set([code.split(' ')[0] for code in Course.objects.values_list('course_code', flat=True)])))
    credit_options = Course.objects.values_list('course_credits', flat=True).distinct().order_by('course_credits')
    return render(request, 'search.html', {
        'courses': page_obj,
        'page_obj': page_obj,
        'page_range': page_range,
        'paginator': paginator,
        'query': query,
        'professors': professors,
        'departments': departments,
        'credit_options': credit_options,
        'selected_department': department,
        'selected_professor': int(professor_id) if professor_id else '',
        'selected_credits': credits,
        'selected_difficulty': difficulty,
    })
def course_detail(request, course_id):
    """Render details, aggregate review scores, and reviews for one course."""
    # Prefetch the many-to-many professor list before rendering the header.
    course = get_object_or_404(
        Course.objects.prefetch_related('course_professors'),
        pk=course_id
    )

    # Reviews are reused for both the list and summary stats; select_related
    # avoids one extra query per review for professor/user/major data.
    reviews = Review.objects.filter(review_course=course).select_related(
        'review_professor',
        'review_user__user_major'
    ).order_by('-review_date', '-id')

    # Aggregate in the database so the page can show summary values without
    # manually iterating over every review in Python.
    review_stats = reviews.aggregate(
        review_count=Count('id'),
        average_difficulty=Avg('difficulty_score'),
        average_time=Avg('time_score')
    )

    return render(request, 'course_detail.html', {
        'course': course,
        'reviews': reviews,
        'review_stats': review_stats
    })

def about(request):
    """Render the static about page."""
    return render(request, "about.html")

def login_view(request):
    """Authenticate users and redirect staff users to the admin dashboard."""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password
        )
        if user is None:
            return render(request, 'Registration/login.html', {
                'error': 'Invalid username or password'
            })
        # Check if the user has verified their email
        if not user.is_active:
            # Save user.id in session so they can verify if they navigate away
            request.session["verification_user_id"] = user.id
            return render(request, 'Registration/login.html', {
                'error': 'Your account is not active. Please check your email to verify your account.'
            })

        if user.is_staff:
            login(request, user)
            return redirect('/admin/')
        else:
            # Login successful
            login(request, user)
            return redirect('home')


    return render(request, 'Registration/login.html')


def register_view(request):
    """Create a new user account and sign the user in after registration."""
    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST['email'].strip()
        password = request.POST['password']
        password_confirm = request.POST['password_confirm']

        pattern = r"^[A-Za-z0-9._%+-]+@uwm\.edu$"
        username_pattern = r"^[A-Za-z0-9._-]{3,20}$"
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,}$"

        # Check that passwords match
        if password != password_confirm:
            return render(request, 'Registration/register.html', {
                'error': 'Passwords do not match.'
            })
        # Validate username
        if not re.match(username_pattern, username):
            return render(request, "Registration/register.html", {
                "error": "Username must be 3-20 characters and can only contain letters, numbers, periods, underscores, and hyphens."
            })

        # Validate password
        if not re.match(password_pattern, password):
            return render(request, "Registration/register.html", {
                "error": "Password must be at least 8 characters and contain at least one uppercase letter, one lowercase letter, one number, and one special character."
            })

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return render(request, 'Registration/register.html', {
                'error': 'Username already exists.'
            })

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return render(request, "Registration/register.html", {
                "error": "Email already exists."
            })

        # Validate UWM email pattern
        if not re.match(pattern, email):
            return render(request, "Registration/register.html", {
                "error": "Must use a valid UWM email address to register."
            })

        # Create inactive user safely after all validation checks pass
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        user.is_active = False
        user.save()

        # Generate verification code and session values
        code = str(random.randint(100000, 999999))
        request.session["verification_code"] = code
        request.session["verification_user_id"] = user.id

        send_mail(
            "Verify your account",
            f"Your verification code is: {code}",
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@uwm.edu'),
            [user.email],
            fail_silently=False,
        )

        return redirect("verify_email")

    return render(request, 'Registration/register.html')

def verify_email(request):
    """Verify a user's email using the code sent to them."""
    if request.method == 'POST':
        entered_code = request.POST.get('verification_code', '').strip()

        stored_code = request.session.get('verification_code')
        user_id = request.session.get('verification_user_id')

        # Make sure verification information exists
        if not stored_code or not user_id:
            return render(request, 'Registration/verify_email.html', {
                'error': 'Your verification session has expired. Please register again.'
            })

        # Check verification code
        if entered_code != stored_code:
            return render(request, 'Registration/verify_email.html', {
                'error': 'Invalid verification code.'
            })

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return render(request, 'Registration/verify_email.html', {
                'error': 'User account could not be found.'
            })

        # Activate account
        user.is_active = True
        user.save()

        # Clean session details
        request.session.pop('verification_code', None)
        request.session.pop('verification_user_id', None)

        # Log user in
        login(request, user)

        return redirect('home')

    verification_email = None
    user_id = request.session.get('verification_user_id')
    if user_id:
        verification_email = User.objects.filter(id=user_id).values_list(
            'email', flat=True
        ).first()

    return render(request, 'Registration/verify_email.html', {
        'verification_email': verification_email
    })


def resend_verification_code(request):
    """Resend a new verification code to the active registration session user."""
    user_id = request.session.get('verification_user_id')

    if not user_id:
        return redirect('register')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('register')

    # Generate a new code
    code = str(random.randint(100000, 999999))

    # Store code in session
    request.session['verification_code'] = code

    send_mail(
        'Your new verification code',
        f'Your new verification code is: {code}',
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@uwm.edu'),
        [user.email],
        fail_silently=False,
    )

    messages.success(request, 'A new verification code has been sent.')
    return redirect('verify_email')


def forgot_password_view(request):
    """Handle password reset requests."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email=email).first()

        if user:
            # Generate a secure one-time token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Build full URL to reset page
            reset_path = reverse('reset_password_confirm', kwargs={'uidb64': uid, 'token': token})
            reset_url = request.build_absolute_uri(reset_path)

            send_mail(
                "Reset Your Password",
                f"Hello {user.username},\n\nYou requested a password reset. Click the link below to set a new password:\n\n{reset_url}\n\nIf you did not request this, please ignore this email.",
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@uwm.edu'),
                [user.email],
                fail_silently=False,
            )

        # Show success message regardless of whether user was found (security best practice)
        messages.success(request, "If an account with that email exists, we've sent a password reset link.")
        return redirect('login')

    return render(request, 'Registration/forgot_password.html')


def reset_password_confirm_view(request, uidb64, token):
    """Handle the new password submission from the email link."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Verify that token is valid for this user
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')

            if password != password_confirm:
                return render(request, 'Registration/reset_password_confirm.html', {
                    'error': 'Passwords do not match.'
                })

            # Update password and save
            user.set_password(password)
            user.save()

            messages.success(request, 'Your password has been reset successfully. You can now log in.')
            return redirect('login')

        return render(request, 'Registration/reset_password_confirm.html')
    else:
        return render(request, 'Registration/reset_password_confirm.html', {
            'error': 'The password reset link is invalid or has expired.'
        })
def course_lookup(request):
    query = request.GET.get('q', '').strip()

    courses = Course.objects.filter(
        Q(course_code__icontains=query) |
        Q(course_name__icontains=query)
    ).annotate(
        rank=Case(
            When(course_code__istartswith=query, then=Value(0)),
            When(course_code__icontains=query, then=Value(1)),
            When(course_name__istartswith=query, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    ).order_by('rank', 'course_code')

    results = [
        {'id': c.id, 'label': f'{c.course_code} - {c.course_name}'}
        for c in courses[:5]
    ]
    return JsonResponse({'results': results})

@login_required
def my_profile(request):

    username_error = None

    # Method for changing username on the profile page
    if request.method == 'POST':
        new_username = request.POST.get('username')

        # Check if the username already exists
        if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
            username_error = "That username is already taken."
        else:
            request.user.username = new_username
            request.user.save()

    # grabs all the reviews for the logged in user
    reviews = Review.objects.filter(review_user=request.user)

    return render(request, 'my_profile.html', {
        'reviews': reviews,
        'username_error': username_error
    })
"""review page showing all reviews"""
def review_page(request):
    query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'recent')

    # Base queryset prefetching related models for efficiency
    reviews = Review.objects.select_related(
        'review_course',
        'review_professor',
        'review_user__user_major'
    ).annotate(
        # distinct=True stops the two joins from multiplying each other's counts
        upvote_count=Count('review_upvotes', distinct=True),
        comment_count=Count('comments', distinct=True),
    )

    # Whether the current user has upvoted each review (drives the filled heart)
    if request.user.is_authenticated:
        reviews = reviews.annotate(
            user_upvoted=Exists(
                Review.review_upvotes.through.objects.filter(
                    review_id=OuterRef('pk'),
                    user_id=request.user.pk,
                )
            )
        )
    else:
        reviews = reviews.annotate(
            user_upvoted=Value(False, output_field=BooleanField())
        )

    # 1. Search across review text, course code/name, professor name, and author username
    if query:
        reviews = reviews.filter(
            Q(review_text__icontains=query) |
            Q(review_course__course_code__icontains=query) |
            Q(review_course__course_name__icontains=query) |
            Q(review_professor__professor_name__icontains=query) |
            Q(review_user__username__icontains=query)
        )

    # 2. Sorting options
    if sort_by == 'oldest':
        reviews = reviews.order_by('review_date', 'id')
    elif sort_by == 'easiest':
        reviews = reviews.order_by('difficulty_score', '-review_date')
    elif sort_by == 'hardest':
        reviews = reviews.order_by('-difficulty_score', '-review_date')
    else:  # Default to most recent
        reviews = reviews.order_by('-review_date', '-id')

    # Paginate feed (e.g., 10 reviews per page)
    paginator = Paginator(reviews, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'reviewpage.html', {
        'reviews': page_obj,
        'query': query,
        'sort_by': sort_by,
    })

# Comment and upvotes on reviews
# How many comments to load each time "Show more" is clicked
COMMENTS_PER_LOAD = 3
COMMENT_MAX_LENGTH = 1000


def _login_required_json():
    return JsonResponse(
        {'error': 'You must be logged in to do that.', 'login_url': reverse('login')},
        status=401
    )


def _comment_to_dict(comment):
    return {
        'id': comment.id,
        'user': comment.comment_user.username,
        'text': comment.comment_text,
        'date': comment.comment_date.strftime('%b %d, %Y'),
    }


@require_GET
def review_comments(request, review_id):
    """Return the next batch of comments for a review, oldest first.

    Uses ?offset=N to say how many comments the page already has.
    One extra comment is fetched to know whether a "Show more" button
    is needed, without running a separate COUNT query.
    """
    review = get_object_or_404(Review, pk=review_id)

    try:
        offset = max(int(request.GET.get('offset', 0)), 0)
    except ValueError:
        offset = 0

    batch = list(
        review.comments.select_related('comment_user')
        .order_by('comment_date', 'id')[offset:offset + COMMENTS_PER_LOAD + 1]
    )

    return JsonResponse({
        'comments': [_comment_to_dict(c) for c in batch[:COMMENTS_PER_LOAD]],
        'has_more': len(batch) > COMMENTS_PER_LOAD,
    })


@require_POST
def add_comment(request, review_id):
    """Post a new comment under a review."""
    if not request.user.is_authenticated:
        return _login_required_json()

    review = get_object_or_404(Review, pk=review_id)
    text = request.POST.get('comment_text', '').strip()

    if not text:
        return JsonResponse({'error': 'Comment cannot be blank.'}, status=400)
    if len(text) > COMMENT_MAX_LENGTH:
        return JsonResponse(
            {'error': f'Comments can be at most {COMMENT_MAX_LENGTH} characters.'},
            status=400
        )

    comment = Comment.objects.create(
        comment_review=review,
        comment_user=request.user,
        comment_text=text
    )

    return JsonResponse({
        'comment': _comment_to_dict(comment),
        'comment_count': review.comments.count(),
    }, status=201)


@require_POST
def toggle_upvote(request, review_id):
    """Upvote a review, or remove the upvote if the user already upvoted it."""
    if not request.user.is_authenticated:
        return _login_required_json()

    review = get_object_or_404(Review, pk=review_id)

    if review.review_upvotes.filter(pk=request.user.pk).exists():
        review.review_upvotes.remove(request.user)
        upvoted = False
    else:
        review.review_upvotes.add(request.user)
        upvoted = True

    return JsonResponse({
        'upvoted': upvoted,
        'upvote_count': review.review_upvotes.count(),
    })


def calculator(request):
    #Course take average difficulty, average time, and number of reviews
    courses = Course.objects.annotate(
        avg_difficulty=Avg('review__difficulty_score'),
        avg_time=Avg('review__time_score'),
        review_count=Count('review')
    ).order_by('course_code')

    # Handle saving schedule to a user who is logged in
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to save your schedule.")
            return redirect('login')

        selected_course_ids = request.POST.getlist('selected_courses')
        request.user.saved_courses.set(selected_course_ids)
        messages.success(request, "Your course schedule has been saved to your account!")
        return redirect('calculator')

    # If logged in, get their previously saved courses
    saved_course_ids = []
    if request.user.is_authenticated:
        saved_course_ids = list(request.user.saved_courses.values_list('id', flat=True))

    return render(request, 'calculator.html', {
        'courses': courses,
        'saved_course_ids': saved_course_ids,
    })