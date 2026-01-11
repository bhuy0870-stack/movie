import requests
import re
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from .models import Movie, Watchlist, Review, Achievement, UserAchievement, Episode, Profile

# --- 1. DỮ LIỆU NAVBAR TẬP TRUNG ---
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

# --- 2. HÀM BỔ TRỢ (ACHIEVEMENTS) ---
def check_and_assign_achievement(request, user, achievement_id):
    achievement = Achievement.objects.filter(id=achievement_id).first()
    if achievement:
        already_has = UserAchievement.objects.filter(user=user, achievement=achievement).exists()
        if not already_has:
            UserAchievement.objects.create(user=user, achievement=achievement)
            messages.success(request, f"🏆 Bạn nhận được huy hiệu: {achievement.name}")

# --- 3. HIỂN THỊ PHIM ---

def home(request):
    query = request.GET.get('q') # <--- LẤY TỪ KHÓA TỪ URL
    genre_slug = request.GET.get('genre')
    country_slug = request.GET.get('country')
    year_selected = request.GET.get('year')
    page_number = request.GET.get('page')

    # Defer description để tăng tốc độ load query ban đầu
    movies_list = Movie.objects.all().order_by('-id').defer('description')

    # Map từ slug sang tên Tiếng Việt để tìm kiếm trong chuỗi văn bản của OPhim
    genre_map = {item['slug']: item['name'] for item in NAV_CONTEXT['genre_list']}
    country_map = {item['slug']: item['name'] for item in NAV_CONTEXT['country_list']}

    # --- ĐOẠN NÀY LÀ LOGIC TÌM KIẾM KHI NHẤN ENTER ---
    if query:
        movies_list = movies_list.filter(
            Q(title__icontains=query) | Q(origin_name__icontains=query)
        )
    
    # LỌC THEO THỂ LOẠI: Quét cả Slug và Tên Tiếng Việt để mục nào cũng hiện
    if genre_slug and genre_slug != 'all':
        keyword = genre_map.get(genre_slug)
        if keyword:
            movies_list = movies_list.filter(
                Q(genres__icontains=keyword) | Q(genres__icontains=genre_slug)
            )
        else:
            movies_list = movies_list.filter(genres__icontains=genre_slug.replace('-', ' '))
        
    # LỌC THEO QUỐC GIA
    if country_slug:
        keyword = country_map.get(country_slug)
        if keyword:
            movies_list = movies_list.filter(
                Q(country__icontains=keyword) | Q(country__icontains=country_slug)
            )
        else:
            movies_list = movies_list.filter(country__icontains=country_slug.replace('-', ' '))

    # LỌC THEO NĂM
    if year_selected and year_selected != 'all':
        movies_list = movies_list.filter(release_date__icontains=str(year_selected))

    # Phân trang (18 phim mỗi trang)
    paginator = Paginator(movies_list, 20)
    movies_page = paginator.get_page(page_number)
    
    # Top Phim hot dựa trên IMDB
    hot_movies = Movie.objects.all().order_by('-imdb_rating')[:10]

    context = {
        **NAV_CONTEXT,
        'movies_page': movies_page,
        'hot_movies': hot_movies,
        'current_genre': genre_slug,
        'current_country': country_slug,
        'current_year': year_selected,
        'query': query, # Trả ngược query ra để template biết đang search gì
    }
    return render(request, 'main/home.html', context)

def movie_detail(request, slug=None):
    # Hỗ trợ tìm theo ID hoặc Slug
    if slug and str(slug).isdigit():
        movie = get_object_or_404(Movie, id=slug)
    else:
        movie = get_object_or_404(Movie, slug=slug)
        
    reviews = Review.objects.filter(movie=movie).select_related('user', 'user__profile').prefetch_related('user__achievements__achievement').order_by('-created_at')
    
    is_bookmarked = request.user.is_authenticated and Watchlist.objects.filter(user=request.user, movie=movie).exists()
    episodes = movie.episodes.all().order_by('id')
    default_video_url = episodes.first().link_ophim if episodes.exists() else ""
    
    # Kiểm tra giới hạn tuổi dựa trên last_name (lưu ngày sinh)
    can_watch, age_message = True, ""
    if movie.age_limit > 0:
        if not request.user.is_authenticated:
            can_watch, age_message = False, "Vui lòng đăng nhập để xem phim này."
        elif request.user.last_name:
            try:
                birth_date = date.fromisoformat(request.user.last_name)
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                if age < movie.age_limit:
                    can_watch, age_message = False, f"Phim giới hạn {movie.age_limit}+. Bạn mới {age} tuổi."
            except:
                can_watch, age_message = False, "Lỗi định dạng ngày sinh."
        else:
            can_watch, age_message = False, "Vui lòng cập nhật ngày sinh trong Profile."

    # Gợi ý phim (Recommendations)
    first_genre = movie.genres.split(',')[0].strip() if movie.genres else ""
    recommendations = Movie.objects.filter(genres__icontains=first_genre).exclude(id=movie.id).only('title', 'slug', 'poster_url', 'imdb_rating', 'release_date')[:6]
    
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

# --- 4. TÌM KIẾM AJAX (QUICK SEARCH) ---
def ajax_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) >= 2:
        movies = Movie.objects.filter(Q(title__icontains=query) | Q(origin_name__icontains=query)).only('id', 'slug', 'title', 'poster_url', 'imdb_rating')[:6]
        results = [{'id': m.id, 'slug': m.slug, 'title': m.title, 'poster': m.poster_url, 'imdb': str(m.imdb_rating)} for m in movies]
        return JsonResponse({'status': 'success', 'data': results})
    return JsonResponse({'status': 'error', 'data': []})

# --- 5. HỆ THỐNG TÀI KHOẢN ---

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
        user.last_name = birth_date
        user.save()
        Profile.objects.get_or_create(user=user)
        login(request, user)
        messages.success(request, f"Chào mừng {username}!")
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

# --- 6. HỒ SƠ & TƯƠNG TÁC ---

@login_required
def profile_view(request):
    user_age = "Chưa xác định"
    if request.user.last_name:
        try:
            birth_date = date.fromisoformat(request.user.last_name)
            user_age = date.today().year - birth_date.year
        except: pass
        
    profile, _ = Profile.objects.get_or_create(user=request.user)
    achievements = UserAchievement.objects.filter(user=request.user).select_related('achievement')
    
    return render(request, 'main/profile.html', {
        'user': request.user, 
        'user_age': user_age, 
        'profile': profile, 
        'achievements': achievements, 
        **NAV_CONTEXT
    })

@login_required
def update_avatar(request):
    if request.method == 'POST' and request.FILES.get('avatar'):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, "Ảnh đại diện đã cập nhật!")
    return redirect('profile')

@login_required
def add_review(request, movie_id):
    if request.method == 'POST':
        movie = get_object_or_404(Movie, pk=movie_id)
        comment_text = request.POST.get('comment', '').strip()
        if comment_text:
            review = Review.objects.create(user=request.user, movie=movie, comment=comment_text, rating=5)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                avatar_url = "https://ui-avatars.com/api/?name=" + request.user.username
                if hasattr(request.user, 'profile') and request.user.profile.avatar:
                    avatar_url = request.user.profile.avatar.url
                medals = [{'name': ua.achievement.name, 'icon': ua.achievement.icon_class, 'color': ua.achievement.color} for ua in request.user.achievements.all()]
                return JsonResponse({
                    'status': 'success',
                    'username': request.user.username,
                    'comment': review.comment,
                    'user_avatar': avatar_url,
                    'review_id': review.id,
                    'achievements': medals
                })
    return redirect('movie_detail', slug=movie.slug)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    review.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def toggle_watchlist(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    # Lấy Profile của user thông qua related_name 'profile' (giả định trong Model Profile đặt như vậy)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    item, created = Watchlist.objects.get_or_create(user=request.user, movie=movie)
    if not created:
        item.delete()
        action = 'removed'
    else:
        action = 'added'
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': action})
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def watchlist_view(request):
    items = Watchlist.objects.filter(user=request.user).select_related('movie')
    return render(request, 'main/watchlist.html', {'items': items, **NAV_CONTEXT})

@login_required
def like_review(request, review_id):
    r = get_object_or_404(Review, id=review_id)
    if r.likes.filter(id=request.user.id).exists():
        r.likes.remove(request.user)
        liked = False
    else:
        r.likes.add(request.user)
        liked = True
    return JsonResponse({'liked': liked, 'count': r.likes.count()})