import os
from pathlib import Path
import dj_database_url
import cloudinary

# --- ĐƯỜNG DẪN CƠ SỞ ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- BẢO MẬT ---
# Render sẽ ưu tiên lấy SECRET_KEY từ môi trường, nếu không có mới dùng key tạm
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-^0d&erhpz6!3xko+=gpco+4psmqdmpt=n%*#h(4ey7iy$8=gmq')

# QUAN TRỌNG: Trên Render PHẢI để DEBUG = False để tránh tràn bộ nhớ
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Điền chính xác domain của bạn vào đây thay vì dấu '*' để Render Health Check chạy được
ALLOWED_HOSTS = ['movie-yu48.onrender.com', 'localhost', '127.0.0.1', '.render.com'] 

# --- ĐỊNH NGHĨA ỨNG DỤNG ---
INSTALLED_APPS = [
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'whitenoise.runserver_nostatic', 
    'django.contrib.staticfiles',
    'main.apps.MainConfig',
    'cloudinary',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]
SITE_ID = 1

# --- MIDDLEWARE (Thứ tự rất quan trọng để tránh Timed Out) ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Phải ở vị trí này
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# --- CƠ SỞ DỮ LIỆU ---
db_url = os.environ.get('DATABASE_URL') or "postgresql://neondb_owner:npg_Vj8TvLxoR6lc@ep-dawn-wildflower-a1ix5r2h-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

DATABASES = {
    'default': dj_database_url.config(
        default=db_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --- CẤU HÌNH STATIC FILES (Sửa lỗi 0 files collected) ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Sử dụng Manifest để hỗ trợ cache file tĩnh tốt hơn trên Render
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- Cấu hình Allauth (Sửa lỗi Warning dẫn đến sập server) ---
ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "none"

# --- AN TOÀN ---
CSRF_TRUSTED_ORIGINS = [
    'https://movie-yu48.onrender.com',
    'https://*.render.com',
]