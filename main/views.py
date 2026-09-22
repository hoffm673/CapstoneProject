from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.db.models import Avg, Count
from .models import User
from .models import Review
from .models import Course, Professor


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
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password_confirm = request.POST['password_confirm']

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

        # Create the user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Log the user in automatically
        login(request, user)

        return redirect('home')

    return render(request, 'Registration/register.html')
