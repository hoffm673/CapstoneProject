from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .models import User
from .models import Review
from .models import Course, Professor


def home(request):
    # Fetch the 2 most recent reviews, ordered by date and id descending
    recent_reviews = Review.objects.select_related(
        'review_course', 
        'review_professor', 
        'review_user__user_major'
    ).order_by('-review_date', '-id')[:2]

    return render(request, 'home.html', {
        'recent_reviews': recent_reviews
    })

def review(request):
    courses = Course.objects.all().order_by('course_code')
    professors = Professor.objects.all().order_by('professor_name')

    return render(request, 'review.html', {
        'courses': courses,
        'professors': professors,
    })

def search(request):
    courses = Course.objects.prefetch_related('course_professors').order_by('course_code')
    return render(request, 'search.html', {
        'courses': courses
    })
def about(request):
    return render(request, "about.html")

def login_view(request):
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
            return redirect('home')
        # Login successful
        login(request, user)

    return render(request, 'Registration/login.html')

def register_view(request):
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