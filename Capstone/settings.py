from pathlib import Path
import os
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-zglql1(qd2a&!$igcbkut52!e4)ut&jsvc38+2($$mlc9u1bt&'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
]

# Use our extended Django User model for authentication
# Just adds user_major to the Django user feature
AUTH_USER_MODEL = 'main.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Capstone.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Capstone.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Use Gmail when credentials are configured. Without credentials, keep local
# registration usable by printing verification messages to the development server.
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or "noreply@uwm.edu"
LOGIN_URL = 'login'

from django.db import migrations

MAJORS = ['Actuarial Science',
 'Administrative Leadership',
 'African and African Diaspora Studies',
 'Air Force and Aerospace Studies',
 'American Indian Studies',
 'American Sign Language',
 'Ancient and Modern Languages, Literatures and Cultures',
 'Anthropology',
 'Applied Computing',
 'Arabic',
 'Architecture',
 'Art Education',
 'Art History',
 'Art and Design',
 'Asian Studies',
 'Astronomy',
 'Athletic Training',
 'Atmospheric Sciences',
 'Biological Sciences',
 'Biomedical Engineering',
 'Biomedical Sciences',
 'Business Administration',
 'Business Management',
 'Celtic Studies',
 'Chemistry and Biochemistry',
 'Chinese',
 'Civil and Environmental Engineering',
 'Classics',
 'College of Health Professions and Sciences',
 'Communication',
 'Communication Sciences and Disorders',
 'Comparative Literature',
 'Computer Science',
 'Computer Studies',
 'Conservation and Environmental Sciences',
 'Counseling',
 'Criminal Justice and Criminology',
 'Curriculum and Instruction',
 'Dance',
 'Diagnostic Imaging',
 'Digital Arts and Culture',
 'Economics',
 'Education-Interdepartmental',
 'Educational Policy and Community Studies',
 'Educational Psychology',
 'Electrical Engineering',
 'Engineering and Applied Science',
 'English',
 'English for Academic Purposes',
 'Ethnic Studies, Comparative',
 'Exceptional Education',
 'Film Studies',
 'Film, Video, Animation and New Genres',
 'Fitness, Wellness and Sport',
 'Food and Beverage Studies',
 'French',
 'Freshwater Sciences',
 'Geography',
 'Geosciences',
 'German',
 'Global Studies',
 'Graduate Studies',
 'Greek',
 'Health Care Administration',
 'Health Care Informatics',
 'Hebrew',
 'History',
 'Hmong Studies',
 'Honors College',
 'Industrial and Labor Relations',
 'Industrial and Manufacturing Engineering',
 'Information Studies',
 'International Studies',
 'Italian',
 'Japanese',
 'Jewish Studies',
 'Journalism, Advertising, and Media Studies',
 'Kinesiology',
 'Korean',
 'Latin',
 'Latin American and Caribbean Studies',
 'Latin American, Caribbean, and U.S. Latinx Studies',
 'Latin American, Caribbean, and U.S. Latinx Studies (LACUSL) T • Teaching and '
 'Learning',
 'Latinx Studies',
 'Lesbian, Gay, Bisexual, and Transgender Studies',
 'Linguistics',
 'Materials Science and Engineering',
 'Mathematical Sciences',
 'Mathematical Statistics',
 'Mechanical Engineering',
 'Military Science',
 'Music',
 'Music Education',
 'Music Performance',
 'Neuroscience',
 'Nonproﬁt Administration',
 'Nursing',
 'Nutritional Sciences',
 'Occupational Therapy',
 'Peace Studies',
 'Performance Rehabilitation and Performance Psychology',
 'Performance Rehabilitation and Performance Psychology (PRPP) Mathematics '
 '(FM) Professional Actuarial Exam. (p. 2056) Prerequisites: a grade of C or '
 'better in MATH 211(P) or MATH 232(P). • Philosophy',
 'Physical Therapy',
 'Physics',
 'Polish',
 'Political Science',
 'Portuguese',
 'Psychology',
 'Public Administration',
 'Public Health',
 'Religious Studies',
 'Russian',
 'Social Work',
 'Sociology',
 'Spanish',
 'Sustainable Peacebuilding, Master of',
 'Theatre',
 'Therapeutic Recreation',
 'Translation and Interpreting',
 'UWS Collaborative Nursing Program',
 'Urban Planning',
 'Urban Studies Program',
 "Women's and Gender Studies",
 'World Languages and Cultures']


def add_majors(apps, schema_editor):
    Major = apps.get_model("yourapp", "Major")
    for name in MAJORS:
        Major.objects.get_or_create(major_name=name)


def remove_majors(apps, schema_editor):
    Major = apps.get_model("yourapp", "Major")
    Major.objects.filter(major_name__in=MAJORS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("yourapp", "0004_previous_migration"),  # leave what Django generated
    ]

    operations = [
        migrations.RunPython(add_majors, remove_majors),
    ]