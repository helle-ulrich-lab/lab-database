from pathlib import Path
from .private_settings import *


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Application definition

INSTALLED_APPS = [
    'adminactions',
    'django.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djangoql',
    'simple_history',
    'import_export',
    'collection',
    'extend_user',
    'ordering',
    'guardian',
    'background_task',
    'formz',
    'approval',
    'common',
    'mozilla_django_oidc',
    'django_better_admin_arrayfield',
    ]

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting' 

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


# Password validation

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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Force specific datetime formats
from django.conf.locale.en import formats as en_formats
en_formats.DATETIME_FORMAT = "j N Y, H:i:s"
en_formats.DATE_FORMAT = "j N Y"

from django.conf.locale.en_GB import formats as en_gb_formats
en_gb_formats.DATETIME_FORMAT = "j N Y, H:i:s"
en_gb_formats.DATE_FORMAT = "j N Y"


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "static",]


# Media files

MEDIA_URL = '/uploads/'
MEDIA_ROOT = BASE_DIR / 'uploads'


#Email/SMTP settings
DEFAULT_FROM_EMAIL = SERVER_EMAIL_ADDRESS

#Email settings for error messages

SERVER_EMAIL = SERVER_EMAIL_ADDRESS
ADMINS = SITE_ADMIN_EMAIL_ADDRESSES


# Plainly stolen from Parkour LIMS :)
# Make sure the 'logs' directory exists. If not, create it
LOG_DIR = BASE_DIR / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "simple": {
            "format": "[%(levelname)s] [%(asctime)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
        "verbose": {
            "format": "[%(levelname)s] [%(asctime)s] [%(pathname)s:%(lineno)s]: %(funcName)s(): %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler"
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "logfile": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "formatter": "verbose",
            "maxBytes": 15 * 1024 * 1024,  # 15 MB
            "backupCount": 2,
        },
        "dblogfile": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "db.log",
            "formatter": "verbose",
            "maxBytes": 15 * 1024 * 1024,
            "backupCount": 2,
        },
    },
    'loggers': {
        'mail_admins': {
            'level': 'ERROR',
            'handlers': ['mail_admins'],
        },
        'console': {
            'level': 'INFO',
            'handlers': ['console'],
        },
        'logfile': {
            'level': 'DEBUG',
            'handlers': ['logfile'],
        },
        'dblogfile': {
            'level': 'DEBUG',
            'handlers': ['dblogfile'],
        },
        'mozilla_django_oidc': {
            'level': 'DEBUG',
            'handlers': ['logfile'],
        },
    }
}


# OIDC settings

LOGIN_REDIRECT_URL = "/login/"
LOGOUT_REDIRECT_URL = "/logout/"
if ALLOW_OIDC:
    AUTHENTICATION_BACKENDS = ['extend_user.oidc.MyOIDCAB'] + AUTHENTICATION_BACKENDS
    MIDDLEWARE += ['mozilla_django_oidc.middleware.SessionRefresh']
OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = 86400 # 24 h


# Other settings

FILE_UPLOAD_PERMISSIONS = 0o664
LOGIN_URL = "/login/"
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
X_FRAME_OPTIONS = 'SAMEORIGIN'
OVE_URL = '/ove/'
MAX_UPLOAD_FILE_SIZE_MB = 2
ALLOWED_DOC_FILE_EXTS = ['pdf', 'zip', '']
