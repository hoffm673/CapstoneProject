from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
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
        review_text = request.POST.get('review_text')

        # Retrieves a course object using the course ID
        course = get_object_or_404(Course, pk=course_id)
        # Retrieves the professor using the professor ID
        professor = get_object_or_404(Professor, pk=professor_id)

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

def search(request):
    """Render the searchable course list."""
    # Prefetch professors because the template lists them for every course.
    courses = Course.objects.prefetch_related('course_professors').order_by('course_code')
    return render(request, 'search.html', {
        'courses': courses
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

        # Check that passwords match
        if password != password_confirm:
            return render(request, 'Registration/register.html', {
                'error': 'Passwords do not match.'
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

        # Dynamically build verification URL
        verify_path = reverse('verify_email')
        verify_url = request.build_absolute_uri(verify_path)

        send_mail(
            "Verify your account",
            f"Your verification code is: {code}\n\nVerify your account here: {verify_url}",
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@uwm.edu'),
            [user.email],
            fail_silently=True,
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

    return render(request, 'Registration/verify_email.html')


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

    verify_url = request.build_absolute_uri('/verify-email/')

    send_mail(
        'Your new verification code',
        f'Your new verification code is: {code}\n\nVerify your account here: {verify_url}',
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@uwm.edu'),
        [user.email],
        fail_silently=True,
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
                fail_silently=True,
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