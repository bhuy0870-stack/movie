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
from .models import Movie, Watchlist, Review, Achievement, UserAchievement, Episode

# --- BIẾN DÙNG CHUNG (Để hiện Navbar ở mọi trang) ---
NAV_CONTEXT = {
    'genre_list': ['Hành động', 'Viễn tưởng', 'Kinh dị', 'Hài hước', 'Tình cảm', 'Hoạt hình', 'Cổ trang', 'Tâm lý'],
    'country_list': ['Việt Nam', 'Trung Quốc', 'Hàn Quốc', 'Nhật Bản', 'Âu Mỹ', 'Thái Lan'],
    'year_list': range(2026, 2018, -1),
}

# --- HELPER FUNCTIONS ---

def check_and_assign_achievement(request, user, achievement_id):
    achievement = Achievement.objects.filter(id=achievement_id).first()
    if achievement:
        already_has = UserAchievement.objects.filter(user=user, achievement=achievement).exists()
        if not already_has:
            UserAchievement.objects.create(user=user, achievement=achievement)
            messages.success(request, f"🏆 Chúc mừng! Bạn vừa nhận được huy hiệu: {achievement.name}")

# --- MAIN VIEWS ---

def home(request):
    search_query = request.GET.get('q', '')
    genre_query = request.GET.get('genre', '')
    country_query = request.GET.get('country', '')
    year_query = request.GET.get('year', '')
    sort_query = request.GET.get('sort', '-id') # Mặc định là mới nhất theo ID

    movies = Movie.objects.all()

    # --- LOGIC TÌM KIẾM & LỌC ---
    if search_query:
        movies = movies.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(origin_name__icontains=search_query)
        )
    if genre_query:
        movies = movies.filter(genres__icontains=genre_query)
    if country_query:
        movies = movies.filter(country__icontains=country_query)
    if year_query:
        movies = movies.filter(release_date__icontains=year_query)

    # --- PHÂN TRANG CHO DANH SÁCH CHÍNH (Phim mới nhất) ---
    all_movies_sorted = movies.order_by(sort_query)
    paginator = Paginator(all_movies_sorted, 20) 
    page_number = request.GET.get('page')
    movies_page = paginator.get_page(page_number)

    # --- PHIM HOT NHẤT (Top Rating / Featured) ---
    # Lấy 10 phim có điểm IMDb cao nhất để hiện ở Sidebar hoặc Section riêng
    hot_movies = Movie.objects.all().order_by('-imdb_rating', '-release_date')[:10]

    # --- PHIM ĐỀ CỬ (Slider) ---
    featured_movies = Movie.objects.filter(imdb_rating__gte=8).order_by('?')[:5]

    context = {
        **NAV_CONTEXT,
        'movies_page': movies_page,     # Đây là phim "Mới nhất" (theo sort_query)
        'hot_movies': hot_movies,       # Đây là phim "Hot nhất"
        'featured_movies': featured_movies,
        'search_query': search_query,
        'current_genre': genre_query,
        'current_country': country_query,
    }
    return render(request, 'main/home.html', context)

def movie_detail(request, slug):
    movie = get_object_or_404(Movie, slug=slug)
    reviews = Review.objects.filter(movie=movie).order_by('-created_at')
    
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = Watchlist.objects.filter(user=request.user, movie=movie).exists()
    
    episodes = movie.episodes.all().order_by('id')
    
    default_video_url = ""
    if episodes.exists():
        first_ep = episodes.first()
        default_video_url = first_ep.link_ophim if first_ep.link_ophim else ""
    
    # Kiểm tra độ tuổi
    can_watch = True
    age_message = ""
    if movie.age_limit > 0:
        if not request.user.is_authenticated:
            can_watch = False
            age_message = "Vui lòng đăng nhập để xem phim này."
        elif request.user.last_name:
            try:
                birth_date = date.fromisoformat(request.user.last_name)
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                if age < movie.age_limit:
                    can_watch = False
                    age_message = f"Phim này giới hạn {movie.age_limit}+. Bạn mới {age} tuổi."
            except:
                can_watch = False
                age_message = "Ngày sinh không hợp lệ."
        else:
            can_watch = False
            age_message = "Cập nhật ngày sinh trong Profile để xem phim này."

    # Gợi ý phim cùng thể loại
    first_genre = movie.genres.split(',')[0].strip() if movie.genres else ""
    recommendations = Movie.objects.filter(genres__icontains=first_genre).exclude(id=movie.id).order_by('-id')[:6]
    
    context = {
        **NAV_CONTEXT, # QUAN TRỌNG: Thêm dòng này để Navbar hiện thể loại/quốc gia
        'movie': movie, 
        'episodes': episodes,
        'default_video_url': default_video_url,
        'reviews': reviews, 
        'recommendations': recommendations, 
        'can_watch': can_watch,
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
            return render(request, 'main/register.html', NAV_CONTEXT)

        if User.objects.filter(username=username).exists():
            messages.error(request, "Tên đăng nhập đã tồn tại!")
            return render(request, 'main/register.html', NAV_CONTEXT)

        user = User.objects.create_user(username=username, email=email, password=password)
        user.last_name = birth_date 
        user.save()
        
        login(request, user)
        check_and_assign_achievement(request, user, 1)
        messages.success(request, f"Chào mừng {username}! Đăng ký thành công.")
        return redirect('home')
            
    return render(request, 'main/register.html', NAV_CONTEXT)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else: 
        form = AuthenticationForm()
    
    context = {'form': form, **NAV_CONTEXT}
    return render(request, 'main/login.html', context)

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
        pos_words = ['hay', 'tốt', 'tuyệt', 'đỉnh', 'cuốn', 'thích']
        neg_words = ['tệ', 'dở', 'chán', 'nhạt', 'phí']
        score = sum(1 for w in pos_words if w in comment_lower) - sum(1 for w in neg_words if w in comment_lower)
        sentiment_label = "Tích cực 😊" if score > 0 else "Tiêu cực 😡" if score < 0 else "Trung lập 😐"

        Review.objects.create(
            user=request.user, movie=movie, 
            comment=comment, rating=rating, sentiment_label=sentiment_label
        )
        
        if Review.objects.filter(user=request.user).count() >= 5:
            check_and_assign_achievement(request, request.user, 2)
            
        messages.success(request, "Đã gửi bình luận!")
    return redirect('movie_detail', slug=movie.slug)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    movie_slug = review.movie.slug
    if review.user == request.user:
        review.delete()
    return redirect('movie_detail', slug=movie_slug)

@login_required
def profile_view(request):
    user_age = "Chưa cập nhật"
    if request.user.last_name:
        try:
            birth_date = date.fromisoformat(request.user.last_name)
            today = date.today()
            user_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except: pass
            
    context = {'user': request.user, 'user_age': user_age, **NAV_CONTEXT}
    return render(request, 'main/profile.html', context)

@login_required
def toggle_watchlist(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    item, created = Watchlist.objects.get_or_create(user=request.user, movie=movie)
    if not created:
        item.delete()
        messages.info(request, "Đã xóa khỏi danh sách lưu.")
    else:
        if Watchlist.objects.filter(user=request.user).count() >= 10:
            check_and_assign_achievement(request, request.user, 3)
        messages.success(request, "Đã lưu phim.")
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def watchlist_view(request):
    items = Watchlist.objects.filter(user=request.user).select_related('movie')
    context = {'items': items, **NAV_CONTEXT}
    return render(request, 'main/watchlist.html', context)

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