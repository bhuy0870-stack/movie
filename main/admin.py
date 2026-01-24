import json
import threading
from datetime import date
from collections import Counter  # <--- Dùng để đếm chữ trong thể loại
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from django.core.management import call_command
from django.utils.html import format_html
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.db.models.functions import TruncMonth 
from .models import Movie, Episode, Review, Achievement, UserAchievement

# --- CẤU HÌNH TIÊU ĐỀ ADMIN ---
admin.site.site_header = "Hệ thống Quản trị Movie Hub"
admin.site.site_title = "BQH MOVIE Admin"
admin.site.index_title = "Bảng điều khiển quản lý Phim"

# --- 1. Quản lý Thành tích ---
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'show_color')
    def show_color(self, obj):
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border-radius: 4px; display: inline-block; margin-right: 10px; border: 1px solid #444; vertical-align: middle;"></div> <code style="color: #ccc;">{}</code>',
            obj.color, obj.color
        )
    show_color.short_description = 'Màu sắc'

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'date_unlocked')
    list_filter = ('achievement', 'date_unlocked')

# --- 2. Quản lý Tập phim ---
class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1
    fields = ('episode_name', 'server_name', 'link_ophim')

# --- 3. Quản lý Phim (Movie) - DASHBOARD ---
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('display_poster', 'title', 'origin_name', 'release_date', 'current_episode', 'updated_at')
    list_filter = ('is_series', 'country', 'release_date', 'updated_at')
    search_fields = ('title', 'origin_name', 'slug')
    inlines = [EpisodeInline]
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    change_list_template = "admin/movie_dashboard.html"

    def display_poster(self, obj):
        if obj.poster_url:
            return format_html('<img src="{}" width="40" height="55" style="border-radius: 4px; object-fit: cover; border: 1px solid #444;" />', obj.poster_url)
        return "No Image"
    display_poster.short_description = 'Poster'

    # --- TÍNH TOÁN SỐ LIỆU ---
    def changelist_view(self, request, extra_context=None):
        # 1. Tổng quan
        total_movies = Movie.objects.count()
        total_reviews = Review.objects.count()
        avg_data = Review.objects.aggregate(Avg('rating'))
        avg_site_rating = avg_data['rating__avg'] if avg_data['rating__avg'] else 0
        
        # 2. Phim Lẻ vs Phim Bộ
        series_data = Movie.objects.values('is_series').annotate(count=Count('id'))
        pie_labels = ["Phim Lẻ", "Phim Bộ"]
        pie_data = [0, 0]
        for item in series_data:
            if item['is_series']: pie_data[1] = item['count']
            else: pie_data[0] = item['count']

        # 3. Top Phim (Dùng 'reviews' thay vì 'review')
        top_movies = Movie.objects.annotate(review_count=Count('reviews')).order_by('-review_count')[:5]
        bar_labels = [m.title[:20] + '...' if len(m.title) > 20 else m.title for m in top_movies]
        bar_data = [m.review_count for m in top_movies]

        # 4. Tăng trưởng User
        monthly_users = User.objects.filter(is_active=True).annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(count=Count('id')).order_by('month')

        user_labels = []
        user_data = []
        for entry in monthly_users:
            if entry['month']:
                user_labels.append(entry['month'].strftime("%m/%Y"))
                user_data.append(entry['count'])
        user_labels = user_labels[-6:]
        user_data = user_data[-6:]

        # 5. Top Thể loại (XỬ LÝ CHUỖI TEXT)
        # Lấy tất cả các dòng genres ra (dạng list các string)
        all_genres_text = Movie.objects.values_list('genres', flat=True)
        genre_counter = Counter()

        for g_text in all_genres_text:
            if g_text: # Nếu không rỗng
                # Tách chuỗi theo dấu phẩy, ví dụ: "Hành động, Phiêu lưu" -> ["Hành động", "Phiêu lưu"]
                # strip() để xóa khoảng trắng thừa
                g_list = [g.strip() for g in str(g_text).split(',') if g.strip()]
                genre_counter.update(g_list)
        
        # Lấy top 5 cái xuất hiện nhiều nhất
        most_common_genres = genre_counter.most_common(5)
        genre_labels = [item[0] for item in most_common_genres]
        genre_data = [item[1] for item in most_common_genres]

        extra_context = extra_context or {}
        extra_context['stats'] = {
            'total_movies': total_movies,
            'total_reviews': total_reviews,
            'avg_rating': round(avg_site_rating, 1),
            'pie_labels': json.dumps(pie_labels),
            'pie_data': json.dumps(pie_data),
            'bar_labels': json.dumps(bar_labels),
            'bar_data': json.dumps(bar_data),
            'user_labels': json.dumps(user_labels),
            'user_data': json.dumps(user_data),
            'genre_labels': json.dumps(genre_labels), # Giờ đã có dữ liệu thật
            'genre_data': json.dumps(genre_data),
        }
        return super().changelist_view(request, extra_context=extra_context)

    # --- NÚT CHỨC NĂNG ---
    def get_urls(self):
        urls = super().get_urls()
        return [
            path('crawl-now/', self.admin_site.admin_view(self.crawl_now_view), name='movie-crawl-now'),
            path('sync-tmdb-now/', self.admin_site.admin_view(self.sync_tmdb_view), name='movie-sync-tmdb'),
        ] + urls

    def crawl_now_view(self, request):
        def run():
            try: call_command('crawl_movies', start=1, end=2)
            except Exception as e: print(f"Lỗi: {e}")
        threading.Thread(target=run).start()
        return JsonResponse({'status': 'success', 'message': '🚀 Đang cào phim...'})

    def sync_tmdb_view(self, request):
        def run():
            try: call_command('update_tmdb')
            except Exception as e: print(f"Lỗi: {e}")
        threading.Thread(target=run).start()
        return JsonResponse({'status': 'success', 'message': '🎬 Đang update TMDB...'})

# --- 4. Quản lý Đánh giá ---
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating_star', 'created_at')
    list_filter = ('rating', 'created_at')
    
    def rating_star(self, obj):
        return format_html('<span style="color: #ffcc00;">{}</span>', '★' * obj.rating)
    rating_star.short_description = 'Sao'

# --- 5. Quản lý User ---
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'display_age', 'is_staff')
    
    def display_age(self, obj):
        if obj.last_name:
            try:
                bdate = date.fromisoformat(obj.last_name)
                age = date.today().year - bdate.year
                color = "#28a745" if age >= 18 else "#ffc107"
                return format_html('<b style="color: {};">{} tuổi</b>', color, age)
            except: pass
        return "N/A"
    display_age.short_description = 'Tuổi'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)