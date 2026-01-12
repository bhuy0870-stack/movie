from .models import WatchHistory

def global_nav_data(request):
    """
    Hàm này sẽ tự động gửi danh sách Thể loại & Quốc gia 
    vào TẤT CẢ các trang HTML mà không cần khai báo ở views.py.
    Đồng thời lấy thêm 5 phim xem gần nhất để hiển thị ở Navbar.
    """
    GENRES_DATA = [
        {'name': 'Hành động', 'slug': 'hanh-dong'},
        {'name': 'Viễn tưởng', 'slug': 'vien-tuong'},
        {'name': 'Kinh dị', 'slug': 'kinh-di'},
        {'name': 'Hài hước', 'slug': 'hai-huoc'},
        {'name': 'Tình cảm', 'slug': 'tinh-cam'},
        {'name': 'Hoạt hình', 'slug': 'hoat-hinh'},
        {'name': 'Cổ trang', 'slug': 'co-trang'},
        {'name': 'Tâm lý', 'slug': 'tam-ly'},
        {'name': 'TV Show', 'slug': 'tv-show'},
    ]

    COUNTRIES_DATA = [
        {'name': 'Việt Nam', 'slug': 'viet-nam'},
        {'name': 'Trung Quốc', 'slug': 'trung-quoc'},
        {'name': 'Hàn Quốc', 'slug': 'han-quoc'},
        {'name': 'Nhật Bản', 'slug': 'nhat-ban'},
        {'name': 'Âu Mỹ', 'slug': 'au-my'},
        {'name': 'Thái Lan', 'slug': 'thai-lan'},
    ]

    # --- PHẦN LẤY LỊCH SỬ XEM PHIM CHO NAVBAR ---
    recent_history_nav = []
    if request.user.is_authenticated:
        # Lấy 5 phim xem gần đây nhất, dùng select_related để tối ưu tốc độ load
        recent_history_nav = WatchHistory.objects.filter(
            user=request.user
        ).select_related('movie')[:5]

    return {
        'genre_list': GENRES_DATA,
        'country_list': COUNTRIES_DATA,
        'recent_history_nav': recent_history_nav, # Biến này sẽ dùng trong base.html
    }