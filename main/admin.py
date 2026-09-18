from django.contrib import admin
from .models import User, Major, Professor, Course, Review

#User Admin
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'user_major', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    list_filter = ('user_major', 'is_staff', 'is_active')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'course_code',
        'course_name',
        'course_credits',
        'display_professors'
    )

    def display_professors(self, obj):
        return ", ".join(
            professor.name for professor in obj.course_professors.all()
        )

    display_professors.short_description = 'Professors'
    search_fields = (
        'course_code',
        'course_name'
    )
@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('professor_name',)
    search_fields = ('professor_name',)
@admin.register(Review)
class Reviews(admin.ModelAdmin):
    list_display = (
        'review_user',
        'review_course',
        'review_professor',
        'difficulty_score'
    )
    search_fields = (
        'review_user',
        'review_course'
    )



