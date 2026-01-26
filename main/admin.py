import json
import threading
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from django.core.management import call_command
from django.utils.html import format_html
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.db.models.functions import TruncMonth
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import Movie, Episode, Review, Achievement, UserAchievement, Profile

# --- 1. CẤU HÌNH GIAO DIỆN ADMIN ---
admin.site.site_header = mark_safe('<span style="color: #ffcc00; font-weight: 800; font-size: 18px;"><i class="fas fa-film"></i> BQH MOVIE CENTER</span>')
admin.site.site_title = "BQH Admin"
admin.site.index_title = "Tổng quan hệ thống"

# --- 2. MIXIN CSS (Giao diện Dark Mode & Badge đẹp) ---
class MediaMixin:
    class Media:
        css = { 'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',) }
        extra_css = """
            <style>
                :root { --primary-color: #c40000; --bg-dark: #121212; --bg-card: #1e1e1e; --text-color: #e0e0e0; }
                body { background-color: #f4f6f9; }
                .admin-dark-mode body { background-color: var(--bg-dark); color: var(--text-color); }
                /* Badge Style */
                .badge { padding: 5px 10px; border-radius: 6px; font-weight: 600; font-size: 11px; color: #fff; display: inline-block; min-width: 60px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); letter-spacing: 0.5px; }
                .badge-success { background: linear-gradient(135deg, #28a745, #20c997); } 
                .badge-warning { background: linear-gradient(135deg, #ffc107, #fd7e14); color: #000; }
                .badge-danger { background: linear-gradient(135deg, #dc3545, #c40000); } 
                .badge-info { background: linear-gradient(135deg, #17a2b8, #0dcaf0); } 
                .badge-primary { background: linear-gradient(135deg, #0d6efd, #6610f2); }
                /* Rating Bar */
                .rating-bar-container { width: 80px; height: 6px; background: #333; border-radius: 3px; overflow: hidden; display: inline-block; vertical-align: middle; margin-right: 5px; }
                .rating-bar-fill { height: 100%; border-radius: 3px; }
            </style>
        """

# --- 3. QUẢN LÝ THÀNH TÍCH (ACHIEVEMENTS) ---
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin, MediaMixin):
    list_display = ('name', 'preview_icon', 'total_unlocks', 'description')
    change_list_template = "admin/achievement_dashboard.html"

    def preview_icon(self, obj):
        return format_html('<div style="background: {}; color: #000; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; box-shadow: 0 2px 5px rgba(0,0,0,0.3);"><i class="{}"></i></div>', obj.color, obj.icon_class)
    preview_icon.short_description = "Icon"

    def total_unlocks(self, obj):
        count = UserAchievement.objects.filter(achievement=obj).count()
        return format_html('<b style="color: #28a745;">{}</b> người dùng', count)
    total_unlocks.short_description = "Đã đạt"

    def changelist_view(self, request, extra_context=None):
        # Data cho Dashboard
        total_badges = Achievement.objects.count()
        total_unlocks = UserAchievement.objects.count()
        
        # Top 5 Badge phổ biến
        top = UserAchievement.objects.values('achievement__name').annotate(c=Count('id')).order_by('-c')[:5]
        bar_labels = [item['achievement__name'] for item in top]
        bar_data = [item['c'] for item in top]

        # Pie Chart
        users_with_badge = UserAchievement.objects.values('user').distinct().count()
        total_users = User.objects.count()
        pie_labels = ["Đã có thành tích", "Chưa có gì"]
        pie_data = [users_with_badge, total_users - users_with_badge]

        extra_context = extra_context or {}
        extra_context['stats'] = {
            'total_badges': total_badges, 'total_unlocks': total_unlocks,
            'bar_labels': json.dumps(bar_labels), 'bar_data': json.dumps(bar_data),
            'pie_labels': json.dumps(pie_labels), 'pie_data': json.dumps(pie_data),
        }
        return super().changelist_view(request, extra_context=extra_context)

# --- 4. QUẢN LÝ TẬP PHIM (INLINE) - ĐÃ CẬP NHẬT ---
class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 1  # Để sẵn 1 dòng trống để nhập tập mới cho lẹ
    fields = ('episode_name', 'server_name', 'link_ophim', 'created_at')
    readonly_fields = ('created_at',)
    # classes = ('collapse',)  <-- ĐÃ BỎ DÒNG NÀY ĐỂ LUÔN HIỆN TẬP PHIM
    show_change_link = True

# --- 5. QUẢN LÝ PHIM (MOVIE) - ĐÃ CẬP NHẬT ---
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin, MediaMixin):
    save_on_top = True
    # Thêm 'episode_status' vào danh sách hiển thị
    list_display = ('display_thumb', 'info_column', 'episode_status', 'stats_column', 'rating_visual', 'updated_at')
    list_display_links = ('display_thumb', 'info_column')
    list_filter = ('is_series', 'country', 'release_date')
    search_fields = ('title', 'slug', 'origin_name')
    inlines = [EpisodeInline]
    list_per_page = 15
    change_list_template = "admin/movie_dashboard.html"
    
    fieldsets = (
        ('ℹ️ Thông tin cơ bản', {'fields': (('title', 'origin_name'), 'slug', ('is_series', 'country'), 'genres')}),
        ('🖼️ Media & Thời gian', {'fields': (('poster_url', 'thumb_url'), 'release_date')}),
        ('📊 Chỉ số & Tập phim', {'fields': (('imdb_rating', 'age_limit'), ('total_episodes', 'current_episode'))}),
    )

    # Hiển thị ảnh nhỏ
    def display_thumb(self, obj):
        img = obj.thumb_url or obj.poster_url
        return format_html('<img src="{}" style="width: 45px; height: 65px; object-fit: cover; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.3);" />', img) if img else "No Img"
    display_thumb.short_description = "Poster"

    # Cột thông tin chính
    def info_column(self, obj):
        badge = "badge-info" if obj.is_series else "badge-success"
        type_txt = "SERIES" if obj.is_series else "MOVIE"
        return format_html('<div style="font-weight:bold; font-size:14px; margin-bottom:4px;">{}</div><div class="badge {}">{}</div>', obj.title, badge, type_txt)
    info_column.short_description = "Phim / Loại"

    # --- MỚI: CỘT HIỂN THỊ SỐ TẬP ---
    def episode_status(self, obj):
        current = obj.episodes.count()
        total = obj.total_episodes or "?"
        # Màu xanh nếu đã ra đủ tập (hoặc hơn), màu vàng nếu chưa
        try:
            is_full = int(current) >= int(total) if str(total).isdigit() else False
        except:
            is_full = False
            
        color = "#28a745" if is_full else "#ffc107"
        return format_html('<b style="color:{}; font-size:16px;">{}</b> / <span style="color:#aaa">{}</span> tập', color, current, total)
    episode_status.short_description = "Tiến độ"

    # Cột thống kê
    def stats_column(self, obj): return format_html('<i class="fas fa-comment-alt" style="color:#aaa;"></i> <b>{}</b> Reviews', obj.reviews.count())
    stats_column.short_description = "Tương tác"

    # Cột Rating trực quan
    def rating_visual(self, obj):
        p = (obj.imdb_rating or 0) * 10
        c = "#28a745" if p >= 75 else ("#ffc107" if p >= 50 else "#dc3545")
        return format_html('<div class="rating-bar-container"><div class="rating-bar-fill" style="width:{}%; background:{};"></div></div> <b>{}</b>', p, c, obj.imdb_rating)
    rating_visual.short_description = "IMDB"

    # --- ĐỊNH NGHĨA URL TÙY CHỈNH ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('crawl-now/', self.admin_site.admin_view(self.crawl_now_view), name='custom_movie_crawl'),
            path('sync-tmdb-now/', self.admin_site.admin_view(self.sync_tmdb_view), name='custom_movie_sync'),
        ]
        return custom_urls + urls

    def crawl_now_view(self, request):
        threading.Thread(target=lambda: call_command('crawl_movies', start=1, end=2)).start()
        return JsonResponse({'status': 'success', 'message': '🚀 Lệnh Cào Phim đang chạy ngầm!'})

    def sync_tmdb_view(self, request):
        threading.Thread(target=lambda: call_command('update_tmdb')).start()
        return JsonResponse({'status': 'success', 'message': '🎬 Lệnh Đồng bộ TMDB đang chạy ngầm!'})

    # Logic Dashboard
    def changelist_view(self, request, extra_context=None):
        total = Movie.objects.count()
        reviews = Review.objects.count()
        avg = Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0
        series = Movie.objects.filter(is_series=True).count()
        
        pie_data = [total - series, series] 
        
        top = Movie.objects.annotate(rc=Count('reviews')).order_by('-rc')[:5]
        bar_lbl = [m.title[:20] + "..." if len(m.title) > 20 else m.title for m in top]
        bar_val = [m.rc for m in top]

        extra_context = extra_context or {}
        extra_context['stats'] = {
            'total_movies': total, 'total_reviews': reviews, 'avg_rating': round(avg, 1),
            'pie_labels': json.dumps(["Phim Lẻ", "Phim Bộ"]), 'pie_data': json.dumps(pie_data),
            'bar_labels': json.dumps(bar_lbl), 'bar_data': json.dumps(bar_val),
        }
        return super().changelist_view(request, extra_context=extra_context)

# --- 6. QUẢN LÝ REVIEW ---
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin, MediaMixin):
    list_display = ('user', 'movie', 'rating_star', 'comment_trunc', 'created_at')
    list_filter = ('rating', 'created_at')
    change_list_template = "admin/review_dashboard.html"

    def rating_star(self, obj):
        c = "#ffc107" if obj.rating >= 4 else "#ccc"
        return format_html('<span style="color:{}; font-size:14px;">{}</span>', c, '★' * obj.rating)
    rating_star.short_description = "Đánh giá"

    def comment_trunc(self, obj): return (obj.comment[:50] + "...") if obj.comment else ""
    comment_trunc.short_description = "Nội dung"

    def changelist_view(self, request, extra_context=None):
        total = Review.objects.count()
        avg = Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0
        five_star = Review.objects.filter(rating=5).count()
        
        dist = Review.objects.values('rating').annotate(c=Count('id')).order_by('rating')
        rating_map = {1:0, 2:0, 3:0, 4:0, 5:0}
        for d in dist: rating_map[d['rating']] = d['c']
        bar_lbl = ["1★", "2★", "3★", "4★", "5★"]
        bar_val = list(rating_map.values())

        trend = Review.objects.annotate(m=TruncMonth('created_at')).values('m').annotate(c=Count('id')).order_by('m')
        line_lbl = [t['m'].strftime("%m/%Y") for t in trend][-6:]
        line_val = [t['c'] for t in trend][-6:]

        extra_context = extra_context or {}
        extra_context['stats'] = {
            'total_reviews': total, 'avg_rating': round(avg, 1), 'five_star': five_star,
            'bar_labels': json.dumps(bar_lbl), 'bar_data': json.dumps(bar_val),
            'line_labels': json.dumps(line_lbl), 'line_data': json.dumps(line_val),
        }
        return super().changelist_view(request, extra_context=extra_context)

# --- 7. QUẢN LÝ USER ---
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fk_name = 'user'
    verbose_name_plural = "Hồ sơ mở rộng"

class UserAchievementInline(admin.TabularInline):
    model = UserAchievement
    extra = 0
    verbose_name_plural = "Thành tích đã đạt"

class CustomUserAdmin(UserAdmin, MediaMixin):
    inlines = (ProfileInline, UserAchievementInline)
    list_display = ('username', 'email', 'is_active', 'is_staff', 'date_joined', 'achievements_badge')
    change_list_template = "admin/user_dashboard.html"
    
    def achievements_badge(self, obj):
        c = obj.achievements.count()
        return format_html('<span class="badge badge-warning">{} 🏆</span>', c) if c else "-"
    achievements_badge.short_description = "Huy hiệu"

    def changelist_view(self, request, extra_context=None):
        total = User.objects.count()
        active = User.objects.filter(is_active=True).count()
        new_month = User.objects.filter(date_joined__month=timezone.now().month).count()
        
        pie_lbl = ["Hoạt động", "Vô hiệu hóa"]
        pie_val = [active, total - active]

        growth = User.objects.annotate(m=TruncMonth('date_joined')).values('m').annotate(c=Count('id')).order_by('m')
        line_lbl = [g['m'].strftime("%m/%Y") for g in growth][-6:]
        line_val = [g['c'] for g in growth][-6:]

        extra_context = extra_context or {}
        extra_context['stats'] = {
            'total_users': total, 'active_users': active, 'new_month': new_month,
            'pie_labels': json.dumps(pie_lbl), 'pie_data': json.dumps(pie_val),
            'line_labels': json.dumps(line_lbl), 'line_data': json.dumps(line_val),
        }
        return super().changelist_view(request, extra_context=extra_context)

# Unregister User cũ và Register User mới
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)

# --- 8. GLOBAL DASHBOARD (TRANG CHỦ) ---
original_index = admin.site.index
def custom_admin_index(request, extra_context=None):
    stats = {
        'total_movies': Movie.objects.count(),
        'total_episodes': Episode.objects.count(),
        'total_users': User.objects.count(),
        'total_reviews': Review.objects.count(),
        'new_movies_month': Movie.objects.filter(created_at__month=timezone.now().month).count(),
        'new_users_month': User.objects.filter(date_joined__month=timezone.now().month).count(),
        'movie_single': Movie.objects.filter(is_series=False).count(),
        'movie_series': Movie.objects.filter(is_series=True).count(),
        'avg_rating': round(Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0, 1)
    }
    
    last_6m = timezone.now() - timezone.timedelta(days=180)
    u_grow = User.objects.filter(date_joined__gte=last_6m).annotate(m=TruncMonth('date_joined')).values('m').annotate(c=Count('id')).order_by('m')
    r_grow = Review.objects.filter(created_at__gte=last_6m).annotate(m=TruncMonth('created_at')).values('m').annotate(c=Count('id')).order_by('m')
    
    lbls, u_data, r_data = [], [], []
    r_map = {i['m'].strftime("%m/%Y"): i['c'] for i in r_grow}
    
    for i in u_grow:
        m = i['m'].strftime("%m/%Y")
        lbls.append(m)
        u_data.append(i['c'])
        r_data.append(r_map.get(m, 0))

    stats.update({'chart_labels': json.dumps(lbls), 'chart_user': json.dumps(u_data), 'chart_review': json.dumps(r_data)})
    extra_context = extra_context or {}
    extra_context['dashboard_stats'] = stats
    return original_index(request, extra_context=extra_context)

admin.site.index = custom_admin_index