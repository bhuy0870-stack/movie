from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from main.sitemaps import MovieSitemap # Đảm bảo file main/sitemaps.py đã tồn tại
from django.http import HttpResponse

# Khai báo các sitemap
sitemaps = {
    'movies': MovieSitemap,
}

# Hàm tạo robots.txt nhanh gọn
def robots_txt(request):
    content = f"User-agent: *\nDisallow: /admin/\nAllow: /\nSitemap: https://movie-yu48.onrender.com/sitemap.xml"
    return HttpResponse(content, content_type="text/plain")

urlpatterns = [
    # Quản trị hệ thống
    path('admin/', admin.site.urls), 
    
    # Điều hướng về ứng dụng chính
    path('', include('main.urls')), 
    
    # Xác thực (nếu bạn có dùng allauth)
    path('accounts/', include('allauth.urls')),

    # --- SEO: SITEMAP & ROBOTS ---
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt),

]

# Cấu hình hiển thị ảnh/static
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)