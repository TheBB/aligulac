"""
Django settings for aligulac project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


import aligulac.local as local

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = local.SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# CUSTOM

PROJECT_PATH = local.PROJECT_PATH
DUMP_PATH = local.DUMP_PATH
BACKUP_PATH = local.BACKUP_PATH
INTERNAL_IPS = local.INTERNAL_IPS

CACHES = {
    'default': {
        'BACKEND': local.CACHE_BACKEND,
    }
}

# RATINGS

INACTIVE_THRESHOLD = 4
INIT_DEV = 0.23
DECAY_DEV = 0.065
MIN_DEV = 0.04
OFFLINE_WEIGHT = 1.5
PRF_NA = -1000
PRF_INF = -2000
PRF_MININF = -3000

def start_rating(country, period):
    return 0.2 if country == 'KR' else 0.0


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'blog',
    'faq',
    'formulation',
    'miniURL',
    'ratings',
]

if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')

INSTALLED_APPS.append('south')

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'aligulac.urls'

WSGI_APPLICATION = 'aligulac.wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'aligulac',
        'USER': local.DB_USER,
        'PASSWORD': local.DB_PASSWORD,
    }
}

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'

TEMPLATE_DIRS = local.TEMPLATE_DIRS
