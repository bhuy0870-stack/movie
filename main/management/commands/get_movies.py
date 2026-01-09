from django.core.management.base import BaseCommand
from main.models import Movie
import requests
import time
from concurrent.futures import ThreadPoolExecutor # Kỹ thuật đa luồng

class Command(BaseCommand):
    help = 'Load nhanh hàng nghìn phim từ TMDB bằng đa luồng'

    # Cấu hình hằng số
    API_KEY = '640d361bde1790dea88b0c75524307d4'
    BASE_URL = "https://api.themoviedb.org/3"
    
    GENRE_MAP = {
        28: "Hành động", 12: "Phiêu lưu", 16: "Hoạt hình", 35: "Hài", 
        80: "Tội phạm", 18: "Chính kịch", 27: "Kinh dị", 878: "Viễn tưởng", 
        10749: "Tình cảm", 9648: "Bí ẩn", 53: "Giật gân", 14: "Fantasy",
        36: "Lịch sử", 10752: "Chiến tranh", 37: "Viễn tây"
    }

    COUNTRY_MAP = {
        'US': 'Âu Mỹ', 'VN': 'Việt Nam', 'KR': 'Hàn Quốc', 
        'JP': 'Nhật Bản', 'CN': 'Trung Quốc', 'TH': 'Thái Lan',
        'FR': 'Pháp', 'GB': 'Anh'
    }

    def handle(self, *args, **kwargs):
        start_time = time.time()
        self.stdout.write(self.style.HTTP_INFO('--- ĐANG BẮT ĐẦU QUY TRÌNH LOAD PHIM CẤP TỐC ---'))

        # Sử dụng ThreadPoolExecutor để chạy đa luồng
        # max_workers=10 nghĩa là chạy 10 trang cùng lúc
        with ThreadPoolExecutor(max_workers=10) as executor:
            pages = range(1, 51) # Load 50 trang ~ 1000 phim
            executor.map(self.fetch_page, pages)

        end_time = time.time()
        total_time = round(end_time - start_time, 2)
        self.stdout.write(self.style.SUCCESS(f'--- HOÀN THÀNH! Đã quét xong 1000 phim trong {total_time} giây ---'))

    def fetch_page(self, page):
        """Hàm lấy danh sách phim của một trang"""
        # Thử lấy cả phim Phổ biến (popular) và phim Đánh giá cao (top_rated) để đa dạng
        category = "popular" if page % 2 == 0 else "top_rated"
        url = f"{self.BASE_URL}/movie/{category}?api_key={self.API_KEY}&language=vi-VN&page={page}"
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                movies = response.json().get('results', [])
                for item in movies:
                    self.process_movie(item)
                self.stdout.write(f"-> Đã nạp xong trang {page} ({category})")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Lỗi tại trang {page}: {e}"))

    def process_movie(self, item):
        """Hàm xử lý và lưu phim vào Database"""
        try:
            m_id = item['id']
            
            # Lấy thông tin bổ trợ (Chạy tuần tự trong luồng con)
            trailer = self.get_trailer(m_id)
            director, cast = self.get_credits(m_id)
            age_limit = self.get_age_limit(m_id)
            
            # Xử lý Quốc gia
            origin_countries = item.get('origin_country', [])
            country_code = origin_countries[0] if origin_countries else "US"
            country_name = self.COUNTRY_MAP.get(country_code, "Âu Mỹ")

            # Xử lý Ảnh và Thể loại
            poster_path = item.get('poster_path')
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750?text=No+Image"
            
            genre_ids = item.get('genre_ids', [])
            genre_names = ", ".join([self.GENRE_MAP.get(gid, "Phim hay") for gid in genre_ids[:3]])

            # Link xem phim tự động
            auto_movie_url = f"https://vidsrc.to/embed/movie/{m_id}"

            # Lưu vào DB
            Movie.objects.update_or_create(
                api_id=m_id,
                defaults={
                    'title': item['title'],
                    'description': item['overview'] or "Nội dung phim đang được cập nhật...",
                    'release_date': item.get('release_date') or None,
                    'poster_url': poster_url,
                    'trailer_url': trailer,
                    'genres': genre_names,
                    'director': director,
                    'cast': cast,
                    'age_limit': age_limit,
                    'country': country_name,
                    'imdb_rating': item.get('vote_average', 0.0),
                    'movie_url': auto_movie_url
                }
            )
        except Exception:
            pass # Bỏ qua nếu một phim bị lỗi để tiếp tục phim khác

    def get_trailer(self, m_id):
        url = f"{self.BASE_URL}/movie/{m_id}/videos?api_key={self.API_KEY}"
        try:
            res = requests.get(url, timeout=5).json()
            for vid in res.get('results', []):
                if vid['site'] == 'YouTube' and vid['type'] in ['Trailer', 'Teaser']:
                    return f"https://www.youtube.com/watch?v={vid['key']}"
        except: pass
        return ""

    def get_credits(self, m_id):
        url = f"{self.BASE_URL}/movie/{m_id}/credits?api_key={self.API_KEY}&language=vi-VN"
        try:
            res = requests.get(url, timeout=5).json()
            directors = [m['name'] for m in res.get('crew', []) if m['job'] == 'Director']
            cast = [m['name'] for m in res.get('cast', [])[:5]]
            return ", ".join(directors), ", ".join(cast)
        except: return "", ""

    def get_age_limit(self, m_id):
        url = f"{self.BASE_URL}/movie/{m_id}/release_dates?api_key={self.API_KEY}"
        try:
            res = requests.get(url, timeout=5).json()
            for r in res.get('results', []):
                if r['iso_3166_1'] in ['VN', 'US']:
                    cert = r['release_dates'][0].get('certification', '')
                    mapping = {'18': 18, 'R': 18, 'T18': 18, '16': 16, 'T16': 16, '13': 13, 'PG-13': 13}
                    if cert in mapping: return mapping[cert]
                    if cert.isdigit(): return int(cert)
        except: pass
        return 0