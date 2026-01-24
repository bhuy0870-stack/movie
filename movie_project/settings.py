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
    'jazzmin',
    'django.contrib.sitemaps',
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

# --- CẤU HÌNH ALLAUTH TỐI ƯU (ĐÃ SỬA) ---

# 1. Cấu hình đăng nhập cơ bản
# Sử dụng Email làm phương thức chính để đăng nhập/định danh
ACCOUNT_AUTHENTICATION_METHOD = 'email' 
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True

# 2. Xử lý Username (QUAN TRỌNG)
# Không bắt buộc người dùng nhập username (hệ thống tự sinh ngầm từ email)
ACCOUNT_USERNAME_REQUIRED = False 
# Không hiển thị trường nào trong form đăng ký thêm (để bỏ qua trang Sign Up)
ACCOUNT_SIGNUP_FIELDS = [] 
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username' # Vẫn giữ trường này trong DB
ACCOUNT_PRESERVE_USERNAME_CASING = False

# 3. Bỏ qua xác thực Email (Vì Google đã xác thực rồi)
ACCOUNT_EMAIL_VERIFICATION = 'none'

# 4. Cấu hình Google (Auto Signup)
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True # Bỏ qua trang "Tiếp tục với Google"
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'

# Adapter xử lý logic (Mặc định)
SOCIALACCOUNT_ADAPTER = 'allauth.socialaccount.adapter.DefaultSocialAccountAdapter'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}

# --- CÁC CẤU HÌNH KHÁC GIỮ NGUYÊN ---
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/' # Đổi thành '/' cho gọn thay vì tên view 'home'

# --- CẤU HÌNH AN TOÀN ---
CSRF_TRUSTED_ORIGINS = [
    'https://*.render.com',
    'https://*.onrender.com',
    'https://*.ngrok-free.app',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

JAZZMIN_SETTINGS = {
    "site_title": "BQH Movie Admin",
    "site_header": "Movie Hub",
    "site_brand": "Hệ thống Quản trị Movie Hub",
    "welcome_sign": "Chào mừng Huy đến với trang quản trị Movie Hub",
    "copyright": "BQH Movie Ltd",
    "search_model": ["auth.User", "main.Movie"], # Giúp tìm kiếm nhanh phim từ thanh search của Admin
    "topmenu_links": [
        {"name": "Trang chủ",  "url": "home", "permissions": ["auth.view_user"]},
        {"model": "auth.User"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "main.Movie": "fas fa-film",
        "main.Genre": "fas fa-tags",
    },
    "order_with_respect_to": ["main", "auth"],
}

# Tùy chọn giao diện tối (Dark mode) hoặc màu sắc khác
JAZZMIN_UI_TWEAKS = {
    "theme": "darkly", # Huy có thể đổi thành 'flatly', 'slate', 'lux'...
}



