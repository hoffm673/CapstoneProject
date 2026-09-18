from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('review/', views.review, name='review'),
    path('search/', views.search, name='search'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('about/', views.about, name='about'),
]
