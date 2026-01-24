import json
import threading
from datetime import date, timedelta
from collections import Counter
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from django.core.management import call_command
from django.utils.html import format_html
from django.http import JsonResponse
from django.db.models import Count, Avg, Q
from django.utils import timezone
from .models import Movie, Episode, Review, Achievement, UserAchievement, WatchHistory

# --- CẤU HÌNH TIÊU ĐỀ ADMIN ---
admin.site.site_header = "Hệ thống Quản trị Movie Hub"
admin.site.site_title = "BQH MOVIE Admin"
admin.site.index_title = "Trung tâm điều hành"

# --- 1. QUẢN LÝ THÀNH TÍCH ---
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'show_color')
    def show_color(self, obj):
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border-radius: 4px; display: inline-block; margin-right: 10px; border: 1px solid #444; vertical-align: middle;"></div> <code>{}</code>',
            obj.color, obj.color
        )

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'date_unlocked')
    list_filter = ('achievement', 'date_unlocked')

# --- 2. QUẢN LÝ TẬP PHIM (Inline) ---
class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1
    fields = ('episode_name', 'server_name', 'link_ophim')

# --- 3. QUẢN LÝ PHIM (DASHBOARD PRO MAX) ---
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('display_poster', 'title', 'status_badge', 'stats_info', 'updated_at')
    list_filter = ('is_series', 'country', 'release_date')
    search_fields = ('title', 'origin_name', 'slug')
    inlines = [EpisodeInline]
    ordering = ('-updated_at',)
    
    # Chỉ định file template riêng cho trang danh sách phim
    change_list_template = "admin/movie_dashboard.html"

    def display_poster(self, obj):
        img = obj.poster_url if obj.poster_url else "https://via.placeholder.com/40x55?text=NA"
        return format_html('<img src="{}" width="40" height="55" style="border-radius: 4px; object-fit: cover; border: 1px solid #444;" />', img)
    display_poster.short_description = 'Poster'

    def status_badge(self, obj):
        # Logic: Cảnh báo nếu phim chưa có tập nào
        eps_count = obj.episodes.count()
        if eps_count == 0:
            return format_html('<span style="background:#dc3545; color:#fff; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:bold;">⚠️ Thiếu tập</span>')
        return format_html('<span style="background:#28a745; color:#fff; padding:3px 8px; border-radius:4px; font-size:11px;">✅ {} tập</span>', eps_count)
    status_badge.short_description = 'Trạng thái'

    def stats_info(self, obj):
        reviews = obj.reviews.count()
        return format_html('⭐ <b>{}</b> <span style="color:#888;">({} review)</span>', obj.imdb_rating, reviews)
    stats_info.short_description = 'Chỉ số'

    # --- LOGIC TÍNH TOÁN KPI ---
    def changelist_view(self, request, extra_context=None):
        # 1. Tính toán KPI Tăng trưởng (So với 30 ngày trước)
        today = timezone.now()
        last_month = today - timedelta(days=30)
        
        def get_growth(model, current_count, date_field='created_at'):
            filter_args = {f"{date_field}__lte": last_month}
            prev_count = model.objects.filter(**filter_args).count()
            if prev_count == 0: return 100 if current_count > 0 else 0
            return round(((current_count - prev_count) / prev_count) * 100, 1)

        # Data Phim
        total_movies = Movie.objects.count()
        movie_growth = get_growth(Movie, total_movies)
        
        # Data User (Loại trừ admin)
        total_users = User.objects.filter(is_staff=False).count()
        prev_users = User.objects.filter(is_staff=False, date_joined__lte=last_month).count()
        user_growth = round(((total_users - prev_users) / prev_users * 100), 1) if prev_users > 0 else 0

        # Data Review & AI Sentiment
        total_reviews = Review.objects.count()
        pos_reviews = Review.objects.filter(sentiment_label='POS').count()
        neg_reviews = Review.objects.filter(sentiment_label='NEG').count()
        neu_reviews = total_reviews - pos_reviews - neg_reviews
        
        # Phim cần xử lý gấp (Chưa có tập)
        missing_episodes = Movie.objects.annotate(num_eps=Count('episodes')).filter(num_eps=0).count()

        # 2. DATA BIỂU ĐỒ 1: SENTIMENT AI (Doughnut Chart)
        sentiment_data = [pos_reviews, neu_reviews, neg_reviews]

        # 3. DATA BIỂU ĐỒ 2: TOP THỂ LOẠI (Bar Chart)
        all_genres = Movie.objects.values_list('genres', flat=True)
        c = Counter()
        for g in all_genres:
            if g: c.update([x.strip() for x in str(g).split(',') if x.strip()])
        top_genres = c.most_common(8)
        genre_labels = [x[0] for x in top_genres]
        genre_values = [x[1] for x in top_genres]

        # 4. BẢNG: PHIM BỊ CHÊ NHIỀU (Để Admin fix)
        problematic_movies = Movie.objects.annotate(
            bad_reviews=Count('reviews', filter=Q(reviews__sentiment_label='NEG'))
        ).order_by('-bad_reviews')[:5]

        # 5. BẢNG: TOP THÀNH VIÊN TÍCH CỰC
        top_users = User.objects.annotate(
            review_count=Count('review') # Lưu ý: 'review' là related_name mặc định nếu chưa đặt trong models
        ).order_by('-review_count')[:5]

        extra_context = extra_context or {}
        extra_context['dashboard'] = {
            'kpi': {
                'movies': {'val': total_movies, 'growth': movie_growth},
                'users': {'val': total_users, 'growth': user_growth},
                'reviews': {'val': total_reviews},
                'missing_eps': missing_episodes,
                'ai_pos_pct': round(pos_reviews/total_reviews*100) if total_reviews else 0
            },
            'charts': {
                'sentiment': json.dumps(sentiment_data),
                'genre_labels': json.dumps(genre_labels),
                'genre_values': json.dumps(genre_values),
            },
            'tables': {
                'problems': problematic_movies,
                'top_users': top_users
            }
        }
        return super().changelist_view(request, extra_context=extra_context)

    # --- NÚT CHỨC NĂNG ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('crawl-now/', self.admin_site.admin_view(self.crawl_now_view), name='movie-crawl-now'),
            path('sync-tmdb-now/', self.admin_site.admin_view(self.sync_tmdb_view), name='movie-sync-tmdb'),
        ]
        return custom_urls + urls

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

# --- 4. QUẢN LÝ ĐÁNH GIÁ (REVIEW) ---
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating_star', 'ai_sentiment', 'created_at')
    list_filter = ('sentiment_label', 'rating', 'created_at')
    search_fields = ('comment', 'user__username', 'movie__title')
    readonly_fields = ('sentiment_label', 'sentiment_score')

    def rating_star(self, obj):
        return format_html('<span style="color: #ffcc00;">{}</span>', '★' * obj.rating)
    rating_star.short_description = 'Sao'

    def ai_sentiment(self, obj):
        if not obj.sentiment_label: return "Chưa phân tích"
        if obj.sentiment_label == 'POS':
            return format_html('<span style="background:#28a745; color:#fff; padding:4px 8px; border-radius:10px; font-size:11px;">😊 Tích cực</span>')
        elif obj.sentiment_label == 'NEG':
            return format_html('<span style="background:#dc3545; color:#fff; padding:4px 8px; border-radius:10px; font-size:11px;">😡 Tiêu cực</span>')
        else:
            return format_html('<span style="background:#6c757d; color:#fff; padding:4px 8px; border-radius:10px; font-size:11px;">😐 Trung lập</span>')
    ai_sentiment.short_description = 'AI Cảm xúc'

# --- 5. QUẢN LÝ USER ---
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'display_age', 'is_staff', 'date_joined')
    
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