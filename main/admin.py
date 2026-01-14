from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django.urls import path
from django.core.management import call_command
from django.contrib import messages
from django.utils.html import format_html
from .models import Movie, Episode, Review, Achievement, UserAchievement
from datetime import date

# 1. Quản lý Thành tích (Achievement)
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'show_color')
    
    def show_color(self, obj):
        # Hiển thị ô màu thực tế trong danh sách admin cho dễ nhìn
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

# 2. Quản lý Tập phim (Inline)
class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1
    # Chỉ giữ lại các trường cần thiết để cào phim Ophim nhanh hơn
    fields = ('episode_name', 'server_name', 'link_ophim')

# 3. Quản lý Phim (Movie)
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    # list_display giúp bạn nhìn nhanh trạng thái cập nhật trên Render
    list_display = ('title', 'origin_name', 'release_date', 'current_episode', 'updated_at')
    list_filter = ('is_series', 'country', 'release_date', 'updated_at')
    search_fields = ('title', 'origin_name', 'slug')
    inlines = [EpisodeInline]
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')

    # Template này chứa các nút bấm "Cào phim"
    change_list_template = "admin/movie_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('crawl-now/', self.admin_site.admin_view(self.crawl_now_view), name='movie-crawl-now'),
            path('sync-tmdb-now/', self.admin_site.admin_view(self.sync_tmdb_view), name='movie-sync-tmdb'),
        ]
        return custom_urls + urls

    def crawl_now_view(self, request):
        """Cào phim mới từ OPhim (Gọi đúng lệnh crawl_movies)"""
        try:
            # Gọi đúng tên file: crawl_movies.py
            call_command('crawl_movies', start=1, end=2)
            self.message_user(request, "🚀 Lệnh 'crawl_movies' thực thi thành công! Phim đã được cập nhật.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ Lỗi khi chạy crawl_movies: {str(e)}", messages.ERROR)
        return redirect("..")

    def sync_tmdb_view(self, request):
        """Đồng bộ TMDB"""
        try:
            call_command('update_tmdb') 
            self.message_user(request, "🎬 Đã cập nhật Poster và Rating từ TMDB!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ Lỗi TMDB: {str(e)}", messages.ERROR)
        return redirect("..")

# 4. Quản lý Đánh giá (Review)
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'user__username', 'movie__title')

# 5. Quản lý User (Chỉnh sửa hiển thị Tuổi rõ nét)
class CustomUserAdmin(UserAdmin):
    # Thêm các cột tùy chỉnh vào danh sách User
    list_display = ('username', 'email', 'get_birth_date', 'display_age', 'is_staff')

    def get_birth_date(self, obj):
        # Trả về ngày sinh lưu trong last_name
        return obj.last_name if obj.last_name else "Chưa có"
    get_birth_date.short_description = 'Ngày sinh'

    def display_age(self, obj):
        if obj.last_name:
            try:
                birth_date = date.fromisoformat(obj.last_name)
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                
                # Highlight tuổi để admin dễ quản lý độ tuổi xem phim
                color = "green" if age >= 18 else "orange"
                return format_html('<b style="color: {};">{} tuổi</b>', color, age)
            except:
                return format_html('<span style="color: red;">Lỗi định dạng</span>')
        return "N/A"
    display_age.short_description = 'Tuổi'

# Đăng ký lại User Admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)