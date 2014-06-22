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

from django.utils.translation import ugettext_lazy as _

import aligulac.local as local

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = local.SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = local.DEBUG
DEBUG_TOOLBAR = local.DEBUG_TOOLBAR

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['.aligulac.com']

LOCALE_PATHS = local.LOCALE_PATHS
LANGUAGE_CODE = 'en_US'

LANGUAGES = [
    ('en', 'English'),
    ('no', 'Norsk'),
]

if DEBUG:
    LANGUAGES += [
        ('zh', '中文(简化字)'),
        ('ru', 'Русский'),
        ('es', 'Español'),
        ('de', 'Deutsch'),
        ('fr', 'Français'),
    ]

# CUSTOM

PROJECT_PATH = local.PROJECT_PATH
DUMP_PATH = local.DUMP_PATH
BACKUP_PATH = local.BACKUP_PATH
INTERNAL_IPS = local.INTERNAL_IPS
EXCHANGE_ID = local.EXCHANGE_ID

CACHES = {
    'default': {
        'BACKEND': local.CACHE_BACKEND,
        'LOCATION': local.CACHE_LOCATION,
    }
}

CACHE_TIMES = {
    # Trivially constant pages, one day
    'aligulac.views.h404': 24*60*60,
    'aligulac.views.h500': 24*60*60,
    'ratings.inference_views.predict': 24*60*60,

    # Views that change only after the quad-daily update can have six hours cache times
    # These typically depend on ratings, but not on specific results
    'aligulac.views.home': 6*60*60,
    'aligulac.views.home': 6*60*60,
    'ratings.inference_views.dual': 6*60*60,
    'ratings.inference_views.sebracket': 6*60*60,
    'ratings.inference_views.rrgroup': 6*60*60,
    'ratings.inference_views.proleague': 6*60*60,
    'ratings.player_views.historical': 6*60*60,
    'ratings.ranking_views.periods': 6*60*60,
    'ratings.ranking_views.period': 6*60*60,
    'ratings.records_views.history': 6*60*60,
    'ratings.records_views.hof': 6*60*60,
    'ratings.records_views.race': 6*60*60,
    'ratings.report_views.balance': 6*60*60,

    # Depends on results but not urgent
    'ratings.misc_views.clocks': 30*60,

    # Set until the queries have been improved
    'ratings.results_views.results': 10*60
}

# RATINGS

INACTIVE_THRESHOLD = 4
INIT_DEV = 0.16
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
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tastypie',
    'blog',
    'faq',
    'formulation',
    'miniURL',
    'ratings',
]

if DEBUG and DEBUG_TOOLBAR:
    INSTALLED_APPS.append('debug_toolbar')

INSTALLED_APPS.append('south')

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG_TOOLBAR:
    MIDDLEWARE_CLASSES.append('debug_toolbar.middleware.DebugToolbarMiddleware')

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

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': local.ERROR_LOG_FILE
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': True
        }
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

SHOW_PER_LIST_PAGE = 40
