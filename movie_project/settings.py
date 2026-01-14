import os
from pathlib import Path
import dj_database_url
import cloudinary

# --- ĐƯỜNG DẪN CƠ SỞ ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- BẢO MẬT ---
SECRET_KEY = 'django-insecure-^0d&erhpz6!3xko+=gpco+4psmqdmpt=n%*#h(4ey7iy$8=gmq'

# DEBUG nên để True khi sửa máy
DEBUG = True

ALLOWED_HOSTS = ['*'] 

# --- ĐỊNH NGHĨA ỨNG DỤNG ---
INSTALLED_APPS = [
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    
    'django.contrib.sites',        # Chỉ giữ lại 1 dòng duy nhất ở đây
    'whitenoise.runserver_nostatic', 
    'django.contrib.staticfiles',
    'main.apps.MainConfig',
    'cloudinary',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google', # Provider Google
    'pwa',
]
SITE_ID = 1

# --- CẤU HÌNH CLOUDINARY ---
cloudinary.config( 
  cloud_name = os.environ.get('CLOUD_NAME', 'your_fallback_name'), 
  api_key = os.environ.get('API_KEY', 'your_fallback_key'), 
  api_secret = os.environ.get('API_SECRET', 'your_fallback_secret'), 
  secure = True
)

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage' 

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
    'allauth.account.middleware.AccountMiddleware',
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

# --- CƠ SỞ DỮ LIỆU ---
db_url = os.environ.get('DATABASE_URL') or "postgresql://neondb_owner:npg_Vj8TvLxoR6lc@ep-dawn-wildflower-a1ix5r2h-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

DATABASES = {
    'default': dj_database_url.config(
        default=db_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --- NGÔN NGỮ VÀ MÚI GIỜ ---
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# --- CẤU HÌNH STATIC FILES ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- CẤU HÌNH ALLAUTH (LOGIN GOOGLE) ---
SITE_ID = 1
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = 'home'

# --- PHẦN SỬA ĐỂ VÀO THẲNG TRANG CHỦ ---
SOCIALACCOUNT_AUTO_SIGNUP = True      # Tự động tạo user từ thông tin Google
SOCIALACCOUNT_LOGIN_ON_GET = True     # Đăng nhập ngay khi bấm nút
ACCOUNT_EMAIL_REQUIRED = True         # Bắt buộc email
ACCOUNT_UNIQUE_EMAIL = True           # Email là duy nhất
ACCOUNT_USERNAME_REQUIRED = False     # Không bắt nhập username thủ công
ACCOUNT_EMAIL_VERIFICATION = "none"   # Bỏ qua xác thực email rườm rà
# --------------------------------------

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    }
}

# --- CẤU HÌNH AN TOÀN ---
CSRF_TRUSTED_ORIGINS = [
    'https://*.render.com',
    'https://*.onrender.com',
    'https://*.ngrok-free.app',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- CẤU HÌNH PWA (APP) ---
PWA_APP_NAME = 'BQH MOVIE'
PWA_APP_DESCRIPTION = "Thế giới phim trong tầm tay"
PWA_THEME_COLOR = '#c40000' # Màu đỏ chủ đạo của bạn
PWA_BACKGROUND_COLOR = '#000000'
PWA_DISPLAY = 'standalone' # Ẩn thanh trình duyệt đi
PWA_SCOPE = '/'
PWA_START_URL = '/'
PWA_APP_ICONS = [
    {
        'src': '/static/images/icon-192.png',
        'sizes': '192x192'
    },
    {
        'src': '/static/images/icon-512.png',
        'sizes': '512x512'
    }
]
PWA_APP_ICONS_APPLE = [
    {
        'src': '/static/images/icon-192.png',
        'sizes': '192x192'
    }
]
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static', 'serviceworker.js')