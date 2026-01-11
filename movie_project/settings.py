import os
from pathlib import Path
import dj_database_url  # THÊM DÒNG NÀY

# --- ĐƯỜNG DẪN CƠ SỞ ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- BẢO MẬT ---
SECRET_KEY = 'django-insecure-^0d&erhpz6!3xko+=gpco+4psmqdmpt=n%*#h(4ey7iy$8=gmq'

# DEBUG nên để True khi sửa máy, trên Render nên để False nhưng có thể để True lúc này để check lỗi
DEBUG = True

ALLOWED_HOSTS = ['*'] 

# --- ĐỊNH NGHĨA ỨNG DỤNG ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', 
    'django.contrib.staticfiles',
    'main.apps.MainConfig',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'movie_project.urls'

# --- GIAO DIỆN (TEMPLATES) ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'main.context_processors.global_nav_data',
            ],
        },
    },
]

WSGI_APPLICATION = 'movie_project.wsgi.application'

# --- CƠ SỞ DỮ LIỆU (ĐÃ CẬP NHẬT CHO NEON) ---
# Huy dán link Postgres copy từ Neon vào dấu ngoặc dưới đây
DATABASE_URL = "postgresql://neondb_owner:npg_Vj8TvLxoR6lc@ep-dawn-wildflower-a1ix5r2h-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --- NGÔN NGỮ VÀ MÚI GIỜ ---
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# --- CẤU HÌNH STATIC FILES (RENDER) ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Hỗ trợ nén file static
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- XÁC THỰC ---
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = 'home'

# --- CẤU HÌNH AN TOÀN ---
CSRF_TRUSTED_ORIGINS = [
    'https://*.render.com',
    'https://*.ngrok-free.app',
    'https://*.ngrok-free.dev',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'