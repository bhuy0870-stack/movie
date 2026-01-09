from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Movie, Review
from datetime import date
from django.contrib import admin
from .models import Achievement, UserAchievement

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color')

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'date_unlocked')

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'release_date', 'age_limit', 'genres')
    list_filter = ('age_limit', 'genres')
    search_fields = ('title', 'director')
    # Hiển thị thêm các cột mới trong danh sách quản lý
    list_display = ('title', 'release_date', 'country', 'is_series', 'imdb_rating')
    # Thêm bộ lọc nhanh ở cột bên phải
    list_filter = ('is_series', 'country', 'release_date')
    # Cho phép tìm kiếm theo tên phim
    search_fields = ('title',)

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

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating', 'sentiment_label', 'created_at')
    list_filter = ('sentiment_label', 'rating')