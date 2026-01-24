import requests
import re
import json
import time
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings

# --- THƯ VIỆN AI ---
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Import Models
from .models import Movie, Watchlist, Review, Achievement, UserAchievement, Episode, Profile, WatchHistory

# ==============================================================================
# 1. CẤU HÌNH AI & VECTOR DB (RAG SYSTEM)
# ==============================================================================

# Cấu hình API Key Gemini
# Lưu ý: Model gemini-1.5-flash yêu cầu thư viện google-generativeai mới nhất
GENAI_API_KEY = "AIzaSyAG6ShAwHw8N3dBbu-fX4s0CTi44Sma0CE" 
genai.configure(api_key=GENAI_API_KEY)

# Load Vector DB
print("⏳ Đang tải mô hình Embeddings & Vector DB...")
embeddings_model = HuggingFaceEmbeddings(model_name="keepitreal/vietnamese-sbert")

try:
    vector_db = FAISS.load_local("ai_index", embeddings_model, allow_dangerous_deserialization=True)
    print("✅ Đã load Vector DB thành công!")
except Exception as e:
    print(f"⚠️ Lỗi load Vector DB: {e}")
    vector_db = None

# ... (Các phần import ở trên giữ nguyên) ...

# ==============================================================================
# 2. VIEW XỬ LÝ AI CHATBOT (CẤU HÌNH CHUẨN 2026)
# ==============================================================================

def ai_chat(request):
    query = request.GET.get('q', '').strip()
    if not query: return JsonResponse({'answer': 'Bạn cần hỏi gì về phim?'})
    
    clean_key = GENAI_API_KEY.strip() if GENAI_API_KEY else ""
    
    if not vector_db:
        return JsonResponse({'answer': 'Hệ thống AI đang khởi động...'})

    try:
        # BƯỚC 1: Tìm kiếm phim (RAG)
        docs = vector_db.similarity_search(query, k=3)
        context_text = ""
        movies_info = []
        for doc in docs:
            context_text += f"- {doc.page_content}\n"
            movies_info.append(doc.metadata)

        # BƯỚC 2: DÙNG MODEL ĐỜI MỚI (Dựa theo danh sách test_key.py của Huy)
        # Ưu tiên: 2.5 Flash (Nhanh) -> 2.5 Pro (Thông minh) -> 2.0 Flash (Backup)
        candidate_models = [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash"
        ]
        
        
        # Tìm đoạn prompt_text cũ và thay bằng đoạn này:
        prompt_text = f"""
        Bạn là "Trợ lý Phim Ảnh BQH" - một chuyên gia điện ảnh vui tính, am hiểu và nhiệt tình.
        
        DỮ LIỆU PHIM TÌM ĐƯỢC TỪ KHO CỦA CHÚNG TA:
        {context_text}
        
        CÂU HỎI CỦA KHÁCH: "{query}"
        
        YÊU CẦU TRẢ LỜI:
        1. Xưng hô là "mình" và gọi khách là "bạn" hoặc "đồng nghiện phim".
        2. Nếu có phim trong danh sách trên, hãy giới thiệu sơ qua (khen phim hay, đáng xem) và dùng icon (🍿, 🎬, 🔥) để sinh động.
        3. Nếu không có phim phù hợp, hãy xin lỗi khéo léo và gợi ý khách tìm từ khóa khác.
        4. Tuyệt đối không bịa ra phim không có trong dữ liệu trên.
        5. Ngắn gọn dưới 3 câu.
        """
        payload = { "contents": [{ "parts": [{"text": prompt_text}] }] }
        
        answer = "Xin lỗi, AI đang bảo trì."

        # Vòng lặp thử các model đời mới
        for model_name in candidate_models:
            # Lưu ý: Các model mới thường dùng endpoint v1beta
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
            try:
                print(f"🔄 Đang gọi model: {model_name}...") 
                response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result['candidates'][0]['content']['parts'][0]['text']
                    print(f"✅ Thành công với {model_name}!")
                    break 
                else:
                    print(f"❌ {model_name} lỗi: {response.status_code}")
            except Exception as err:
                print(f"⚠️ {model_name} mất kết nối: {err}")
                continue 

        return JsonResponse({
            'status': 'success',
            'answer': answer,
            'related_movies': movies_info
        })

    except Exception as e:
        print(f"🔥 Lỗi hệ thống: {e}")
        return JsonResponse({'answer': 'AI đang quá tải.'})

# ==============================================================================
# 3. DỮ LIỆU CHUNG (NAVBAR)
# ==============================================================================
NAV_CONTEXT = {
    'genre_list': [
        {'name': 'Hành động', 'slug': 'hanh-dong'}, {'name': 'Viễn tưởng', 'slug': 'vien-tuong'},
        {'name': 'Kinh dị', 'slug': 'kinh-di'}, {'name': 'Hài hước', 'slug': 'hai-huoc'},
        {'name': 'Tình cảm', 'slug': 'tinh-cam'}, {'name': 'Hoạt hình', 'slug': 'hoat-hinh'},
        {'name': 'Cổ trang', 'slug': 'co-trang'}, {'name': 'Tâm lý', 'slug': 'tam-ly'},
        {'name': 'TV Show', 'slug': 'tv-show'},
    ],
    'country_list': [
        {'name': 'Việt Nam', 'slug': 'viet-nam'}, {'name': 'Trung Quốc', 'slug': 'trung-quoc'},
        {'name': 'Hàn Quốc', 'slug': 'han-quoc'}, {'name': 'Nhật Bản', 'slug': 'nhat-ban'},
        {'name': 'Âu Mỹ', 'slug': 'au-my'}, {'name': 'Thái Lan', 'slug': 'thai-lan'},
    ],
    'year_list': range(2026, 2018, -1),
}

# ==============================================================================
# 4. VIEW CHÍNH: HOME, DETAIL, SEARCH
# ==============================================================================

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
        movies_list = movies_list.filter(genres__icontains=keyword if keyword else genre_slug.replace('-', ' '))
    if country_slug:
        keyword = country_map.get(country_slug)
        movies_list = movies_list.filter(country__icontains=keyword if keyword else country_slug.replace('-', ' '))
    if year_selected and year_selected != 'all':
        movies_list = movies_list.filter(release_date__icontains=str(year_selected))

    paginator = Paginator(movies_list, 24)
    movies_page = paginator.get_page(page_number)
    hot_movies = Movie.objects.all().order_by('-imdb_rating')[:10]

    context = {
        **NAV_CONTEXT, 'movies_page': movies_page, 'hot_movies': hot_movies,
        'current_genre': genre_slug, 'current_country': country_slug,
        'current_year': year_selected, 'query': query, 
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'main/movie_grid.html', context)
    return render(request, 'main/home.html', context)

def movie_detail(request, slug=None):
    if not request.user.is_authenticated:
        messages.warning(request, "Vui lòng đăng nhập để xem chi tiết!")
        return redirect('login')
    
    movie = get_object_or_404(Movie, id=slug) if str(slug).isdigit() else get_object_or_404(Movie, slug=slug)
    
    reviews = Review.objects.filter(movie=movie, parent=None).select_related('user', 'user__profile').prefetch_related('replies').order_by('-created_at')
    
    count_total = reviews.count()
    count_pos = reviews.filter(sentiment_label='POS').count()
    count_neg = reviews.filter(sentiment_label='NEG').count()
    count_neu = count_total - count_pos - count_neg

    can_watch, age_message = True, ""
    if movie.age_limit > 0 and request.user.last_name:
        try:
            bd = date.fromisoformat(request.user.last_name)
            age = (date.today() - bd).days // 365
            if age < movie.age_limit: can_watch, age_message = False, f"Cấm trẻ em dưới {movie.age_limit} tuổi."
        except: pass

    context = {
        **NAV_CONTEXT, 'movie': movie, 
        'episodes': movie.episodes.all().order_by('id'),
        'reviews': reviews, 
        'recommendations': Movie.objects.filter(genres__icontains=movie.genres.split(',')[0].strip()).exclude(id=movie.id)[:6],
        'can_watch': can_watch, 'age_message': age_message,
        'is_bookmarked': Watchlist.objects.filter(user=request.user, movie=movie).exists(),
        'count_total': count_total, 'count_pos': count_pos, 'count_neg': count_neg, 'count_neu': count_neu,
    }
    return render(request, 'main/detail.html', context)

def ajax_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) >= 2:
        movies = Movie.objects.filter(Q(title__icontains=query) | Q(origin_name__icontains=query))[:6]
        results = [{'slug': m.slug, 'title': m.title, 'poster': m.poster_url, 'imdb': str(m.imdb_rating)} for m in movies]
        return JsonResponse({'status': 'success', 'data': results})
    return JsonResponse({'status': 'error', 'data': []})

# ==============================================================================
# 5. HỆ THỐNG TÀI KHOẢN (AUTH)
# ==============================================================================

def register_view(request):
    if request.method == 'POST':
        u, e, p, pc, bd = request.POST.get('username'), request.POST.get('email'), request.POST.get('password'), request.POST.get('password_confirm'), request.POST.get('birth_date')
        if p != pc:
            messages.error(request, "Mật khẩu không khớp!"); return render(request, 'main/register.html', NAV_CONTEXT)
        if User.objects.filter(username=u).exists():
            messages.error(request, "Tên đăng nhập đã tồn tại!"); return render(request, 'main/register.html', NAV_CONTEXT)
            
        user = User.objects.create_user(username=u, email=e, password=p)
        user.last_name = bd; user.save()
        Profile.objects.create(user=user)
        login(request, user)
        return redirect('home')
    return render(request, 'main/register.html', NAV_CONTEXT)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('home')
    return render(request, 'main/login.html', {'form': AuthenticationForm(), **NAV_CONTEXT})

def logout_view(request):
    logout(request)
    return redirect('home')

# ==============================================================================
# 6. PROFILE & TƯƠNG TÁC
# ==============================================================================

@login_required
def profile_view(request):
    if request.method == 'POST':
        bd = request.POST.get('birth_date')
        if bd: request.user.last_name = bd; request.user.save(); messages.success(request, "Đã cập nhật!")
        return redirect('profile')

    user_age = "—"
    if request.user.last_name:
        try: user_age = (date.today() - date.fromisoformat(request.user.last_name)).days // 365
        except: pass

    return render(request, 'main/profile.html', {
        'user_age': user_age, 'profile': Profile.objects.get_or_create(user=request.user)[0],
        'achievements': UserAchievement.objects.filter(user=request.user), 
        'recent_history': WatchHistory.objects.filter(user=request.user)[:3], **NAV_CONTEXT
    })

@login_required
def update_avatar(request):
    if request.method == 'POST' and request.FILES.get('avatar'):
        p, _ = Profile.objects.get_or_create(user=request.user)
        p.avatar = request.FILES['avatar']; p.save()
    return redirect('profile')

@login_required
def add_review(request, movie_id):
    if request.method == 'POST':
        movie = get_object_or_404(Movie, pk=movie_id)
        comment = request.POST.get('comment', '').strip()
        parent_id = request.POST.get('parent_id')
        if comment:
            parent = Review.objects.get(id=parent_id) if parent_id else None
            Review.objects.create(user=request.user, movie=movie, comment=comment, rating=5, parent=parent)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest': return JsonResponse({'status': 'success'})
    return redirect('movie_detail', slug=movie.slug)

@login_required
def delete_review(request, review_id):
    get_object_or_404(Review, pk=review_id, user=request.user).delete()
    return JsonResponse({'status': 'success'}) if request.headers.get('x-requested-with') == 'XMLHttpRequest' else redirect('home')

@login_required
def like_review(request, review_id):
    r = get_object_or_404(Review, id=review_id)
    if request.user in r.likes.all(): r.likes.remove(request.user); liked = False
    else: r.likes.add(request.user); liked = True
    return JsonResponse({'liked': liked, 'count': r.likes.count()})

@login_required
def toggle_watchlist(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    item, created = Watchlist.objects.get_or_create(user=request.user, movie=movie)
    if not created: item.delete()
    return JsonResponse({'status': 'added' if created else 'removed'})

@login_required
def watchlist_view(request):
    return render(request, 'main/watchlist.html', {'items': Watchlist.objects.filter(user=request.user), **NAV_CONTEXT})

@login_required
def update_history(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    WatchHistory.objects.update_or_create(user=request.user, movie=movie)
    return JsonResponse({'status': 'success'})

@login_required
def history_view(request):
    return render(request, 'main/history.html', {'history_list': WatchHistory.objects.filter(user=request.user), **NAV_CONTEXT})

@login_required
def delete_history(request, history_id):
    get_object_or_404(WatchHistory, id=history_id, user=request.user).delete()
    return JsonResponse({'status': 'success'})