from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('review/', views.review, name='review'),
    path('search/', views.search, name='search'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),

#login / register
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('about/', views.about, name='about'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification_code, name='resend_verification'),

# Password Reset
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password_confirm_view, name='reset_password_confirm')
]