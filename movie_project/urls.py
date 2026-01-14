from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Quản trị hệ thống
    path('admin/', admin.site.urls), 
    
    # Điều hướng về ứng dụng chính
    path('', include('main.urls')), 
    path('accounts/', include('allauth.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Cấu hình để hiển thị file static/media trong quá trình phát triển (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)