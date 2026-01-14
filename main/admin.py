from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django.urls import path
from django.core.management import call_command
from django.contrib import messages
from .models import Movie, Episode, Review, Achievement, UserAchievement
from datetime import date

# 1. Quản lý Thành tích
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color')

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'date_unlocked')

# 2. Quản lý Tập phim
class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1
    fields = ('episode_name', 'server_name', 'link_ophim', 'link_bunny_id')

# 3. Quản lý Phim + Nút điều khiển nhanh
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'origin_name', 'release_date', 'country', 'is_series', 'current_episode', 'updated_at')
    list_filter = ('is_series', 'country', 'release_date', 'updated_at')
    search_fields = ('title', 'origin_name', 'slug')
    inlines = [EpisodeInline]
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')

    # Sử dụng template tùy chỉnh để hiện nút bấm
    change_list_template = "admin/movie_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('crawl-now/', self.admin_site.admin_view(self.crawl_now_view), name='movie-crawl-now'),
            path('sync-tmdb-now/', self.admin_site.admin_view(self.sync_tmdb_view), name='movie-sync-tmdb'),
        ]
        return custom_urls + urls

    def crawl_now_view(self, request):
        """Cào phim mới từ OPhim"""
        try:
            call_command('crawl_movies', start=1, end=2)
            self.message_user(request, "🚀 Cập nhật thành công phim mới từ OPhim!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ Lỗi: {str(e)}", messages.ERROR)
        return redirect("..")

    def sync_tmdb_view(self, request):
        """Đồng bộ Poster/Rating từ TMDB cho 100 phim đang thiếu"""
        try:
            # Gọi lệnh update_tmdb (tên file bạn đặt trong ảnh là update_tmdb.py)
            call_command('update_tmdb') 
            self.message_user(request, "🎬 Đã nâng cấp hình ảnh và rating TMDB thành công!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ Lỗi: {str(e)}", messages.ERROR)
        return redirect("..")

# 4. Quản lý Đánh giá
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'user__username', 'movie__title')

# 5. Quản lý User tùy chỉnh
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_birth_date', 'get_age', 'is_staff')

    def get_birth_date(self, obj):
        return obj.last_name if obj.last_name else "Chưa nhập"
    get_birth_date.short_description = 'Ngày sinh'

    def get_age(self, obj):
        if obj.last_name:
            try:
                birth_date = date.fromisoformat(obj.last_name)
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                return f"{age} tuổi"
            except:
                return "Lỗi định dạng"
        return "N/A"
    get_age.short_description = 'Tuổi hiện tại'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)