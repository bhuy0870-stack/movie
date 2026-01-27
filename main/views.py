import requests
import re
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
# Đã thêm Case, When, Value để xử lý logic điều kiện trong DB
from django.db.models import Q, IntegerField, Case, When, Value
# Đã thêm RegexReplace để lọc bỏ ký tự chữ
from django.db.models.functions import Cast, RegexReplace
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from .models import Movie, Watchlist, Review, Achievement, UserAchievement, Episode, Profile, WatchHistory

# --- 1. DỮ LIỆU NAVBAR ---
NAV_CONTEXT = {
    'genre_list': [
        {'name': 'Hành động', 'slug': 'hanh-dong'},
        {'name': 'Viễn tưởng', 'slug': 'vien-tuong'},
        {'name': 'Kinh dị', 'slug': 'kinh-di'},
        {'name': 'Hài hước', 'slug': 'hai-huoc'},
        {'name': 'Tình cảm', 'slug': 'tinh-cam'},
        {'name': 'Hoạt hình', 'slug': 'hoat-hinh'},
        {'name': 'Cổ trang', 'slug': 'co-trang'},
        {'name': 'Tâm lý', 'slug': 'tam-ly'},
        {'name': 'TV Show', 'slug': 'tv-show'},
    ],
    'country_list': [
        {'name': 'Việt Nam', 'slug': 'viet-nam'},
        {'name': 'Trung Quốc', 'slug': 'trung-quoc'},
        {'name': 'Hàn Quốc', 'slug': 'han-quoc'},
        {'name': 'Nhật Bản', 'slug': 'nhat-ban'},
        {'name': 'Âu Mỹ', 'slug': 'au-my'},
        {'name': 'Thái Lan', 'slug': 'thai-lan'},
    ],
    'year_list': range(2026, 2018, -1),
}

# --- 2. HÀM BỔ TRỢ ---
def check_and_assign_achievement(request, user, achievement_id):
    achievement = Achievement.objects.filter(id=achievement_id).first()
    if achievement:
        already_has = UserAchievement.objects.filter(user=user, achievement=achievement).exists()
        if not already_has:
            UserAchievement.objects.create(user=user, achievement=achievement)
            messages.success(request, f"🏆 Bạn nhận được huy hiệu: {achievement.name}")

# --- 3. TRANG CHỦ ---
def home(request):
    query = request.GET.get('q')
    genre_slug = request.GET.get('genre')
    country_slug = request.GET.get('country')
    year_selected = request.GET.get('year') 
    page_number = request.GET.get('page')
    
    movies_list = Movie.objects.all().order_by('-updated_at', '-id').defer('cast', 'director')

    genre_map = {item['slug']: item['name'] for item in NAV_CONTEXT['genre_list']}
    country_map = {item['slug']: item['name'] for item in NAV_CONTEXT['country_list']}

    if query:
        movies_list = movies_list.filter(Q(title__icontains=query) | Q(origin_name__icontains=query))
    
    if genre_slug and genre_slug != 'all':
        keyword = genre_map.get(genre_slug)
        if keyword:
            movies_list = movies_list.filter(Q(genres__icontains=keyword) | Q(genres__icontains=genre_slug))
        else:
            movies_list = movies_list.filter(genres__icontains=genre_slug.replace('-', ' '))
        
    if country_slug:
        keyword = country_map.get(country_slug)
        if keyword:
            movies_list = movies_list.filter(Q(country__icontains=keyword) | Q(country__icontains=country_slug))
        else:
            movies_list = movies_list.filter(country__icontains=country_slug.replace('-', ' '))

    if year_selected and year_selected != 'all':
        movies_list = movies_list.filter(release_date__icontains=str(year_selected))

    paginator = Paginator(movies_list, 24)
    movies_page = paginator.get_page(page_number)
    hot_movies = Movie.objects.all().order_by('-imdb_rating')[:10]

    context = {
        **NAV_CONTEXT,
        'movies_page': movies_page,
        'hot_movies': hot_movies,
        'current_genre': genre_slug,
        'current_country': country_slug,
        'current_year': year_selected,
        'query': query, 
    }
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'main/movie_grid.html', context)
    
    return render(request, 'main/home.html', context)

# --- 4. CHI TIẾT PHIM ---
def movie_detail(request, slug=None):
    if not request.user.is_authenticated:
        messages.warning(request, "Vui lòng đăng nhập để xem chi tiết!")
        return redirect('login')
    
    movie = get_object_or_404(Movie, id=slug) if str(slug).isdigit() else get_object_or_404(Movie, slug=slug)
        
    reviews = Review.objects.filter(movie=movie, parent=None).select_related('user', 'user__profile').prefetch_related('replies', 'replies__user', 'replies__user__profile').order_by('-created_at')    
    is_bookmarked = Watchlist.objects.filter(user=request.user, movie=movie).exists()

    # --- FIX LỖI "596 SP" VÀ SẮP XẾP TẬP PHIM AN TOÀN ---
    episodes = movie.episodes.annotate(
        # 1. Lọc bỏ ký tự không phải số (Ví dụ: "596 SP" -> "596")
        clean_ep_name=RegexReplace('episode_name', r'[^0-9]', Value(''))
    ).annotate(
        # 2. Xử lý logic: Nếu sau khi lọc mà rỗng (không có số) -> gán 0. Nếu có số -> ép kiểu Integer
        ep_num=Case(
            When(clean_ep_name='', then=Value(0)),
            default=Cast('clean_ep_name', output_field=IntegerField()),
            output_field=IntegerField(),
        )
    ).order_by('ep_num', 'id') # Sắp xếp theo số tập, sau đó theo ID

    default_video_url = episodes.first().link_ophim if episodes.exists() else ""
    
    # LOGIC KIỂM TRA TUỔI
    can_watch, age_message = True, ""
    if movie.age_limit > 0:
        # Ưu tiên lấy từ Profile.birth_date
        u_profile = getattr(request.user, 'profile', None)
        b_date = None
        
        if u_profile and u_profile.birth_date:
            b_date = u_profile.birth_date
        elif request.user.last_name: # Fallback dữ liệu cũ
            try: b_date = date.fromisoformat(request.user.last_name)
            except: b_date = None

        if b_date:
            today = date.today()
            age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
            if age < movie.age_limit:
                can_watch, age_message = False, f"Phim giới hạn {movie.age_limit}+. Bạn mới {age} tuổi."
        else:
            can_watch, age_message = False, "Vui lòng cập nhật ngày sinh trong Profile để xem phim này."

    first_genre = movie.genres.split(',')[0].strip() if movie.genres else ""
    recommendations = Movie.objects.filter(genres__icontains=first_genre).exclude(id=movie.id).defer('description')[:6]
    
    context = {
        **NAV_CONTEXT,
        'movie': movie, 
        'episodes': episodes,
        'default_video_url': default_video_url,
        'reviews': reviews, 
        'recommendations': recommendations, 
        'can_watch': can_watch,
        'age_message': age_message,
        'is_bookmarked': is_bookmarked,
    }
    return render(request, 'main/detail.html', context)

# --- Các hàm khác (Search, Account, History,...) giữ nguyên logic của bạn ---
def ajax_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) >= 2:
        movies = Movie.objects.filter(Q(title__icontains=query) | Q(origin_name__icontains=query)).only('id', 'slug', 'title', 'poster_url', 'imdb_rating')[:6]
        results = [{'id': m.id, 'slug': m.slug, 'title': m.title, 'poster': m.poster_url, 'imdb': str(m.imdb_rating)} for m in movies]
        return JsonResponse({'status': 'success', 'data': results})
    return JsonResponse({'status': 'error', 'data': []})

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        birth_date = request.POST.get('birth_date')
        
        if password != password_confirm:
            messages.error(request, "Mật khẩu không khớp!")
            return render(request, 'main/register.html', NAV_CONTEXT)
        if User.objects.filter(username=username).exists():
            messages.error(request, "Tên đăng nhập đã tồn tại!")
            return render(request, 'main/register.html', NAV_CONTEXT)
            
        user = User.objects.create_user(username=username, email=email, password=password)
        if birth_date:
            user.last_name = birth_date
            user.save()
            Profile.objects.update_or_create(user=user, defaults={'birth_date': birth_date})
        
        login(request, user)
        messages.success(request, f"Chào mừng {username} gia nhập BQH MOVIE!")
        return redirect('home')
    return render(request, 'main/register.html', NAV_CONTEXT)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'main/login.html', {'form': form, **NAV_CONTEXT})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def profile_view(request):
    if request.method == 'POST':
        birth_date = request.POST.get('birth_date')
        if birth_date:
            request.user.last_name = birth_date
            request.user.save()
            p, _ = Profile.objects.get_or_create(user=request.user)
            p.birth_date = birth_date
            p.save()
            messages.success(request, "Đã cập nhật ngày sinh!")
        return redirect('profile')

    user_age = "—" 
    b_date = getattr(request.user.profile, 'birth_date', None) or (date.fromisoformat(request.user.last_name) if request.user.last_name else None)
    if b_date:
        today = date.today()
        user_age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))

    profile, _ = Profile.objects.get_or_create(user=request.user)
    achievements = UserAchievement.objects.filter(user=request.user).select_related('achievement')
    recent_history = WatchHistory.objects.filter(user=request.user).select_related('movie')[:3]

    return render(request, 'main/profile.html', {
        'user_age': user_age, 'profile': profile, 'achievements': achievements, 'recent_history': recent_history, **NAV_CONTEXT
    })

@login_required
def update_avatar(request):
    if request.method == 'POST' and request.FILES.get('avatar'):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, "Ảnh đại diện đã được cập nhật!")
    return redirect('profile')

@login_required
def add_review(request, movie_id):
    if request.method == 'POST':
        movie = get_object_or_404(Movie, pk=movie_id)
        comment_text = request.POST.get('comment', '').strip()
        parent_id = request.POST.get('parent_id')
        if comment_text:
            parent_review = Review.objects.filter(id=parent_id).first() if parent_id else None
            review = Review.objects.create(user=request.user, movie=movie, comment=comment_text, rating=5, parent=parent_review)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                avatar_url = request.user.profile.avatar.url if hasattr(request.user, 'profile') and request.user.profile.avatar else f"https://ui-avatars.com/api/?name={request.user.username}"
                medals = [{'name': ua.achievement.name, 'icon': ua.achievement.icon_class, 'color': ua.achievement.color} for ua in request.user.achievements.all()]
                return JsonResponse({'status': 'success', 'username': request.user.username, 'comment': review.comment, 'user_avatar': avatar_url, 'review_id': review.id, 'achievements': medals, 'parent_id': parent_id})
    return redirect('movie_detail', slug=movie.slug)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    review.delete()
    return JsonResponse({'status': 'success'}) if request.headers.get('x-requested-with') == 'XMLHttpRequest' else redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def toggle_watchlist(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    item, created = Watchlist.objects.get_or_create(user=request.user, movie=movie)
    if not created: item.delete()
    return JsonResponse({'status': 'removed' if not created else 'added'}) if request.headers.get('x-requested-with') == 'XMLHttpRequest' else redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def watchlist_view(request):
    items = Watchlist.objects.filter(user=request.user).select_related('movie')
    return render(request, 'main/watchlist.html', {'items': items, **NAV_CONTEXT})

@login_required
def like_review(request, review_id):
    r = get_object_or_404(Review, id=review_id)
    liked = r.likes.filter(id=request.user.id).exists()
    if liked: r.likes.remove(request.user)
    else: r.likes.add(request.user)
    return JsonResponse({'liked': not liked, 'count': r.likes.count()})

@login_required
def update_history(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    WatchHistory.objects.update_or_create(user=request.user, movie=movie)
    return JsonResponse({'status': 'success'})

@login_required
def history_view(request):
    history_list = WatchHistory.objects.filter(user=request.user).select_related('movie')
    return render(request, 'main/history.html', {'history_list': history_list, **NAV_CONTEXT})

@login_required
def delete_history(request, history_id):
    item = get_object_or_404(WatchHistory, id=history_id, user=request.user)
    item.delete()
    return JsonResponse({'status': 'success'})