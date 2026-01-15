import json
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
from datetime import date
import threading # QUAN TRỌNG: Để chạy ngầm không bị timeout

# 1. Quản lý Thành tích
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'show_color')
    def show_color(self, obj):
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

# 2. Quản lý Tập phim
class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1
    fields = ('episode_name', 'server_name', 'link_ophim')

# 3. Quản lý Phim
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'origin_name', 'release_date', 'current_episode', 'updated_at')
    list_filter = ('is_series', 'country', 'release_date', 'updated_at')
    search_fields = ('title', 'origin_name', 'slug')
    inlines = [EpisodeInline]
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')

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
                # Cào nhẹ 2 trang để tránh tràn RAM Render
                call_command('crawl_movies', start=1, end=2)
            except Exception as e:
                print(f"Lỗi cào phim ngầm: {e}")

        # Khởi tạo và chạy luồng riêng
        thread = threading.Thread(target=run_crawl)
        thread.start()

        # Trả về JSON ngay lập tức để JS hiển thị thanh tiến trình giả lập
        return JsonResponse({
            'status': 'success', 
            'message': '🚀 Tiến trình đã bắt đầu! Phim đang được cào ngầm, vui lòng đợi 1-2 phút rồi F5 trang.'
        })

    def sync_tmdb_view(self, request):
        try:
            call_command('update_tmdb') 
            return JsonResponse({'status': 'success', 'message': '🎬 Đồng bộ TMDB thành công!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# 4. Quản lý Đánh giá & User
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'user__username', 'movie__title')

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_birth_date', 'display_age', 'is_staff')
    def get_birth_date(self, obj):
        return obj.last_name if obj.last_name else "Chưa có"
    get_birth_date.short_description = 'Ngày sinh'
    def display_age(self, obj):
        if obj.last_name:
            try:
                birth_date = date.fromisoformat(obj.last_name)
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                color = "green" if age >= 18 else "orange"
                return format_html('<b style="color: {};">{} tuổi</b>', color, age)
            except:
                return format_html('<span style="color: red;">Lỗi định dạng</span>')
        return "N/A"
    display_age.short_description = 'Tuổi'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)