import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'breakthru-secret-dev-replace-in-production-use-strong-entropy')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv(
        'ALLOWED_HOSTS',
        'breakthru.assesment.portal,breakthru.assessment.portal,bt.assesment.pk,bt.assessment.pk,assessment.breakthru.pk,assessments.breakthru.pk,localhost,127.0.0.1,0.0.0.0'
    ).split(',') if h.strip()
]
for domain in ['.breakthru.pk', '.assesment.portal', '.assessment.portal', '.assesment.pk', '.assessment.pk', '.onrender.com', 'testserver']:
    if domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(domain)
if DEBUG and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')

# Production Reverse Proxy & SSL Configuration
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CSRF Trusted Origins for Domain & Cloud Access
CSRF_TRUSTED_ORIGINS = [
    'https://breakthru.assesment.portal',
    'http://breakthru.assesment.portal',
    'https://breakthru.assessment.portal',
    'http://breakthru.assessment.portal',
    'https://bt.assesment.pk',
    'http://bt.assesment.pk',
    'https://bt.assessment.pk',
    'http://bt.assessment.pk',
    'https://assessment.breakthru.pk',
    'https://assessments.breakthru.pk',
    'http://assessment.breakthru.pk',
    'http://assessments.breakthru.pk',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://192.168.18.78:8000',
    'http://10.0.2.84:8000',
    'https://*.pinggy.link',
    'https://*.lhr.life',
    'https://*.trycloudflare.com',
    'https://*.ngrok-free.app',
    'https://*.onrender.com',
]
extra_origins = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if extra_origins:
    for origin in extra_origins.split(','):
        if origin.strip() and origin.strip() not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin.strip())

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',

    # BreakThru Assessments Suite
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'assessments.apps.AssessmentsConfig',
    'exam.apps.ExamConfig',
    'grading.apps.GradingConfig',
    'analytics.apps.AnalyticsConfig',
    'certificates.apps.CertificatesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Custom BreakThru Middlewares
    'core.middleware.AuditLoggingMiddleware',
    'core.middleware.EnforcePasswordChangeMiddleware',
]

ROOT_URLCONF = 'breakthru_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.branding_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'breakthru_portal.wsgi.application'

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')

if DATABASE_URL.startswith('sqlite:'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 60,
                'init_command': 'PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;',
            }
        }
    }
elif DATABASE_URL.startswith('postgres:') or DATABASE_URL.startswith('postgresql:'):
    # Parse standard postgres URL
    import urllib.parse
    url = urllib.parse.urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or '5432',
            'CONN_MAX_AGE': 600,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 60,
                'init_command': 'PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;',
            }
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization & Timezone
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'Asia/Karachi')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Media uploads
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Authentication URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Security & Session Settings
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', '28800'))  # 8 hours
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.getenv('SESSION_EXPIRE_AT_BROWSER_CLOSE', 'False').lower() == 'true'

# Production Security Controls
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1')
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() in ('true', '1')
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True').lower() in ('true', '1')
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email backend (Console in dev, configurable for SMTP in production)
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'BreakThru Assessments <no-reply@breakthru.pk>')
