import os
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY','development-only-not-for-production')
DEBUG=os.environ.get('DJANGO_DEBUG','0')=='1'
from .hosting import host_settings
ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS = host_settings()
INSTALLED_APPS=['django.contrib.admin','django.contrib.messages','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.staticfiles','matching']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.middleware.common.CommonMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','matching.ai_options.OptionalAIMiddleware','matching.middleware.PrivateAppMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
STATIC_URL='/static/'
STATICFILES_DIRS=[BASE_DIR/'static']
STATIC_ROOT=BASE_DIR/'staticfiles'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
SECURE_CONTENT_TYPE_NOSNIFF=True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LOGIN_URL='/login/'
LOGIN_REDIRECT_URL='/'
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SESSION_COOKIE_AGE=8*60*60

# PythonAnywhere terminates HTTPS at its reverse proxy. Recognise the original
# HTTPS scheme so Django's CSRF Origin/Referer checks use the public URL.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
