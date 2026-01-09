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

# Import các model
from .models import Movie, Watchlist, Review, Achievement, UserAchievement

# --- HELPER FUNCTIONS ---

def check_and_assign_achievement(request, user, achievement_id):
    """
    Hàm hỗ trợ kiểm tra và trao huy hiệu cho người dùng
    """
    achievement = Achievement.objects.filter(id=achievement_id).first()
    if achievement:
        already_has = UserAchievement.objects.filter(user=user, achievement=achievement).exists()
        if not already_has:
            UserAchievement.objects.create(user=user, achievement=achievement)
            messages.success(request, f"🏆 Chúc mừng! Bạn vừa nhận được huy hiệu: {achievement.name}")

def fetch_direct_link(tmdb_id):
    providers = [
        f"https://api.consumet.org/meta/tmdb/watch/1?mediaId={tmdb_id}&server=vidsrc",
        f"https://consumet-api-production-e61a.up.railway.app/meta/tmdb/watch/1?mediaId={tmdb_id}",
        f"https://api.veremis.com/tmdb/movie/{tmdb_id}"
    ]
    for url in providers:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                sources = data.get('sources', [])
                if sources:
                    for s in sources:
                        if s.get('quality') in ['auto', 'default']:
                            return s.get('url')
                    return sources[0].get('url')
        except:
            continue 
    return None

def extract_youtube_id(url):
    if not url: return None
    match = re.search(r'(?<=v=)[\w-]+|(?<=youtu\.be/)[\w-]+', url)
    return match.group(0) if match else None

# --- MAIN VIEWS ---

def home(request):
    search_query = request.GET.get('q', '')
    genre_query = request.GET.get('genre', '')
    year_query = request.GET.get('year', '')
    sort_query = request.GET.get('sort', '-release_date')

    movies = Movie.objects.all()

    if search_query:
        movies = movies.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    if genre_query:
        movies = movies.filter(genres__icontains=genre_query)
    if year_query:
        movies = movies.filter(release_date__year=year_query)

    if sort_query == 'views':
        movies = movies.order_by('-imdb_rating')
    else:
        movies = movies.order_by(sort_query)

    paginator = Paginator(movies, 15)
    page_number = request.GET.get('page')
    movies_page = paginator.get_page(page_number)

    featured_movies = Movie.objects.filter(imdb_rating__gte=7).order_by('-release_date')[:5]

    context = {
        'movies_page': movies_page,
        'featured_movies': featured_movies,
        'search_query': search_query,
        'genre_list': ['Hành động', 'Viễn tưởng', 'Kinh dị', 'Hài hước', 'Tình cảm', 'Hoạt hình', 'Cổ trang', 'Tâm lý'],
        'year_list': range(2026, 2018, -1),
        'current_genre': genre_query,
    }
    return render(request, 'main/home.html', context)

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    reviews = Review.objects.filter(movie=movie).order_by('-created_at')
    
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = Watchlist.objects.filter(user=request.user, movie=movie).exists()
    
    episodes = movie.episodes.all() if hasattr(movie, 'episodes') else []
    clean_link = fetch_direct_link(movie.api_id)
    
    if clean_link:
        default_video_url = clean_link
        is_direct = True
    else:
        is_direct = False
        if getattr(movie, 'is_series', False) and episodes:
            default_video_url = episodes.first().video_url
        else:
            default_video_url = movie.movie_url

    can_watch = True
    age_message = ""
    if movie.age_limit > 0:
        if not request.user.is_authenticated:
            can_watch = False
            age_message = "Vui lòng đăng nhập để xem phim này."
        else:
            try:
                birth_date = date.fromisoformat(request.user.last_name)
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                if age < movie.age_limit:
                    can_watch = False
                    age_message = f"Phim này giới hạn {movie.age_limit}+. Bạn mới {age} tuổi."
            except:
                can_watch = False
                age_message = "Cập nhật ngày sinh trong Profile để xem phim này."

    first_genre = movie.genres.split(',')[0].strip() if movie.genres else ""
    recommendations = Movie.objects.filter(genres__icontains=first_genre).exclude(id=movie.id).order_by('-imdb_rating')[:6]
    
    context = {
        'movie': movie, 
        'episodes': episodes,
        'default_video_url': default_video_url,
        'is_direct_link': is_direct,
        'reviews': reviews, 
        'recommendations': recommendations, 
        'can_watch_trailer': can_watch,
        'age_message': age_message,
        'is_bookmarked': is_bookmarked
    }
    return render(request, 'main/detail.html', context)

# --- USER VIEWS ---

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        birth_date = request.POST.get('birth_date')

        if password != password_confirm:
            messages.error(request, "Mật khẩu xác nhận không khớp!")
            return render(request, 'main/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Tên đăng nhập đã tồn tại!")
            return render(request, 'main/register.html')

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.last_name = birth_date 
            user.save()
            
            login(request, user)
            
            # Huy hiệu 1: Thành viên mới
            check_and_assign_achievement(request, user, 1)
            
            messages.success(request, f"Chào mừng {username}! Đăng ký thành công.")
            return redirect('home')
        except Exception as e:
            messages.error(request, f"Lỗi hệ thống: {str(e)}")
            return render(request, 'main/register.html')
            
    return render(request, 'main/register.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(request.POST.get('next', 'home'))
    else: 
        form = AuthenticationForm()
    return render(request, 'main/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required(login_url='login')
def add_review(request, movie_id):
    if request.method == 'POST':
        movie = get_object_or_404(Movie, pk=movie_id)
        comment = request.POST.get('comment', '')
        rating = int(request.POST.get('rating', 5))
        
        comment_lower = comment.lower()
        pos_words = ['hay', 'tốt', 'tuyệt', 'đỉnh', 'cuốn', 'thích', 'đáng xem', 'ý nghĩa', 'xuất sắc', 'hấp dẫn']
        neg_words = ['tệ', 'dở', 'chán', 'nhạt', 'phí', 'không hay', 'vớ vẩn', 'kém', 'thất vọng']

        score = sum(1 for w in pos_words if w in comment_lower) - sum(1 for w in neg_words if w in comment_lower)
        sentiment_label = "Tích cực 😊" if score > 0 else "Tiêu cực 😡" if score < 0 else "Trung lập 😐"

        Review.objects.create(
            user=request.user, movie=movie, 
            comment=comment,
            rating=rating, sentiment_label=sentiment_label
        )
        
        # Huy hiệu 2: Chuyên gia bình luận (Nếu đã có >= 5 bình luận)
        review_count = Review.objects.filter(user=request.user).count()
        if review_count >= 5:
            check_and_assign_achievement(request, request.user, 2)
            
        messages.success(request, "Đã gửi bình luận!")
    return redirect('movie_detail', movie_id=movie_id)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    movie_id = review.movie.id
    if review.user == request.user:
        review.delete()
    return redirect('movie_detail', movie_id=movie_id)

@login_required
def profile_view(request):
    user_age = "Chưa cập nhật"
    if request.user.last_name:
        try:
            birth_date = date.fromisoformat(request.user.last_name)
            today = date.today()
            user_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except: 
            pass
            
    context = {
        'user': request.user,
        'user_age': user_age
    }
    return render(request, 'main/profile.html', context)

@login_required
def toggle_watchlist(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    watchlist_item = Watchlist.objects.filter(user=request.user, movie=movie)
    if watchlist_item.exists():
        watchlist_item.delete()
        messages.info(request, "Đã xóa khỏi danh sách lưu.")
    else:
        Watchlist.objects.create(user=request.user, movie=movie)
        
        # Huy hiệu 3: Nhà sưu tầm (Lưu trên 10 bộ phim)
        collect_count = Watchlist.objects.filter(user=request.user).count()
        if collect_count >= 10:
            check_and_assign_achievement(request, request.user, 3)
            
        messages.success(request, "Đã lưu phim vào danh sách.")
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def watchlist_view(request):
    items = Watchlist.objects.filter(user=request.user).select_related('movie')
    return render(request, 'main/watchlist.html', {'items': items})

@login_required
def like_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    if review.likes.filter(id=request.user.id).exists():
        review.likes.remove(request.user)
        liked = False
    else:
        review.likes.add(request.user)
        liked = True
    return JsonResponse({'liked': liked, 'count': review.likes.count()})