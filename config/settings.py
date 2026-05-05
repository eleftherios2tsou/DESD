"""
Django settings for Bristol Regional Food Network Marketplace
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# load variables from the .env file so we dont hardcode passwords etc
load_dotenv()

# BASE_DIR points to the root of the project (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent

# secret key should be set in .env - the fallback is only for local dev
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-key-change-in-production')

# DEBUG=1 means debug mode is on, set to 0 in production
DEBUG = int(os.environ.get('DEBUG', 1))

# allowing all hosts for now - would lock this down for a real deployment
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'marketplace',       # our main app
    'rest_framework',    # django REST framework for the API (S1-011)
]

# middleware runs on every request - order matters here apparently
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',   # csrf protection on all forms
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # tells django where to look for our html files
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# database config - reads from .env so it works both locally and in docker
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'bristol_marketplace'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),   # 'db' is the docker service name
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# password validators - these enforce rules like min 8 chars etc
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# this tells django to use our custom user model instead of the default one
AUTH_USER_MODEL = 'marketplace.CustomUser'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True

# static files (css, js) are served from /static/
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# uploaded images go into /media/products/
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email — prints to console in development but will set it up for the final sprint review
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Bristol Food Network <noreply@bristolfoodnetwork.co.uk>'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Stripe — set these in your environment or .env file
# Get test keys from https://dashboard.stripe.com/test/apikeys
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')

# DRF config - session auth works with our existing login system
# set page size to 20 so the api doesnt return everything at once
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
