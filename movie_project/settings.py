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
    # Cloudinary storage phải đứng TRƯỚC staticfiles
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    # Whitenoise hỗ trợ static khi chạy server
    'whitenoise.runserver_nostatic', 
    'django.contrib.staticfiles', # CHỈ GIỮ 1 DÒNG NÀY
    'django.contrib.sites',
    'main.apps.MainConfig',
    'cloudinary',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google', # Provider Google
]

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
    'allauth.account.middleware.AccountMiddleware', # Thêm dòng này (thường để cuối cùng)
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
                'django.template.context_processors.request', # Bắt buộc phải có dòng này (check xem có chưa)
            ],
        },
    },
]


WSGI_APPLICATION = 'movie_project.wsgi.application'

# --- CƠ SỞ DỮ LIỆU ---
# Logic: Ưu tiên lấy DATABASE_URL từ môi trường (Render/GitHub), nếu không có mới dùng link dán cứng
db_url = os.environ.get('DATABASE_URL') or "postgresql://neondb_owner:npg_Vj8TvLxoR6lc@ep-dawn-wildflower-a1ix5r2h-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

DATABASES = {
    'default': dj_database_url.config(
        default=db_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Nếu vẫn không cấu hình được database thì dùng SQLite dự phòng
if not DATABASES['default'].get('ENGINE'):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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

# --- CẤU HÌNH ALLAUTH ---
SITE_ID = 1  # Rất quan trọng
LOGIN_REDIRECT_URL = 'home' # Đăng nhập xong nhảy về trang chủ
LOGOUT_REDIRECT_URL = 'home'

# Cấu hình Google Provider
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        # Lấy Client ID và Secret từ biến môi trường (BẢO MẬT)
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
            'key': ''
        }
    }
}
# Không bắt buộc nhập email lại khi đăng nhập gg
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_EMAIL_VERIFICATION = "none"

# Whitenoise cho phép nén file
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- XÁC THỰC ---
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = 'home'

# --- CẤU HÌNH AN TOÀN ---
CSRF_TRUSTED_ORIGINS = [
    'https://*.render.com',
    'https://*.onrender.com', # Render thường dùng domain này
    'https://*.ngrok-free.app',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'