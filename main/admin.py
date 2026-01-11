from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Movie, Episode, Review, Achievement, UserAchievement
from datetime import date

# 1. Quản lý Thành tích
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color')

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'date_unlocked')

# 2. Quản lý Tập phim (Hiển thị ngay bên trong trang sửa phim)
class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1 # Cho phép thêm nhanh 1 tập phim trống
    fields = ('episode_name', 'server_name', 'link_ophim', 'link_bunny_id')

# 3. Quản lý Phim
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    # Cột hiển thị ở danh sách
    list_display = ('title', 'origin_name', 'release_date', 'country', 'is_series', 'current_episode')
    # Bộ lọc ở bên phải
    list_filter = ('is_series', 'country', 'release_date')
    # Ô tìm kiếm
    search_fields = ('title', 'origin_name', 'slug')
    # Tích hợp quản lý tập phim vào trang chi tiết phim
    inlines = [EpisodeInline]

# 4. Quản lý Đánh giá (Đã xóa sentiment_label bị lỗi)
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'user__username', 'movie__title')

# 5. Quản lý User tùy chỉnh (Hiển thị tuổi từ last_name)
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

# Đăng ký lại UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)