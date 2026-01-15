import json
import threading
from datetime import date
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django.urls import path
from django.core.management import call_command
from django.contrib import messages
from django.utils.html import format_html
from django.http import JsonResponse
from .models import Movie, Episode, Review, Achievement, UserAchievement

# --- 1. Quản lý Thành tích (Achievement) ---
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'show_color')
    
    def show_color(self, obj):
        # Hiển thị ô màu thực tế trong danh sách admin
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border-radius: 4px; display: inline-block; margin-right: 10px; border: 1px solid #444;"></div> {}',
            obj.color, obj.color
        )
    show_color.short_description = 'Màu sắc'

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'date_unlocked')
    list_filter = ('achievement', 'date_unlocked')
    search_fields = ('user__username', 'achievement__name')

# --- 2. Quản lý Tập phim (Inline) ---
class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1
    fields = ('episode_name', 'server_name', 'link_ophim')

# --- 3. Quản lý Phim (Movie) ---
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'origin_name', 'release_date', 'current_episode', 'updated_at')
    list_filter = ('is_series', 'country', 'release_date', 'updated_at')
    search_fields = ('title', 'origin_name', 'slug')
    inlines = [EpisodeInline]
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')

    # Template tùy chỉnh để hiện nút bấm cào phim
    change_list_template = "admin/movie_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('crawl-now/', self.admin_site.admin_view(self.crawl_now_view), name='movie-crawl-now'),
            path('sync-tmdb-now/', self.admin_site.admin_view(self.sync_tmdb_view), name='movie-sync-tmdb'),
        ]
        return custom_urls + urls

    def crawl_now_view(self, request):
        """Chạy cào phim dưới dạng Thread ngầm để tránh Render SIGKILL/Timeout"""
        def run_crawl():
            try:
                # Cào 2 trang mới nhất để cập nhật phim
                call_command('crawl_movies', start=1, end=2)
            except Exception as e:
                print(f"Lỗi cào phim ngầm: {e}")

        # Khởi chạy luồng riêng để trả về response ngay lập tức cho trình duyệt
        thread = threading.Thread(target=run_crawl)
        thread.start()

        return JsonResponse({
            'status': 'success', 
            'message': '🚀 Tiến trình đã bắt đầu chạy ngầm! Hệ thống đang cập nhật, vui lòng đợi một chút rồi tải lại trang.'
        })

    def sync_tmdb_view(self, request):
        """Đồng bộ TMDB chạy ngầm tương tự crawl"""
        def run_sync():
            try:
                call_command('update_tmdb')
            except Exception as e:
                print(f"Lỗi TMDB ngầm: {e}")

        thread = threading.Thread(target=run_sync)
        thread.start()

        return JsonResponse({
            'status': 'success', 
            'message': '🎬 Đã bắt đầu đồng bộ Poster/Rating từ TMDB ngầm!'
        })

# --- 4. Quản lý Đánh giá (Review) ---
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'user__username', 'movie__title')

# --- 5. Quản lý User (Tuổi & Ngày sinh) ---
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_birth_date', 'display_age', 'is_staff')

    def get_birth_date(self, obj):
        # Sử dụng last_name để chứa ngày sinh (mẹo nhanh)
        return obj.last_name if obj.last_name else "Chưa có"
    get_birth_date.short_description = 'Ngày sinh'

    def display_age(self, obj):
        if obj.last_name:
            try:
                birth_date = date.fromisoformat(obj.last_name)
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                
                # Highlight tuổi
                color = "green" if age >= 18 else "orange"
                return format_html('<b style="color: {};">{} tuổi</b>', color, age)
            except:
                return format_html('<span style="color: red;">Lỗi định dạng</span>')
        return "N/A"
    display_age.short_description = 'Tuổi'

# Đăng ký lại User Admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)