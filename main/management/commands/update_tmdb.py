import requests
import time
import re
import gc
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Movie

class Command(BaseCommand):
    help = 'Nâng cấp dữ liệu phim từ TMDB (Chạy nối tiếp cho đến khi hết)'

    TMDB_API_KEY = '640d361bde1790dea88b0c75524307d4'

    def handle(self, *args, **options):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        while True:
            # Chỉ lấy phim chưa được tối ưu (rating mặc định 0.0)
            # Dùng .order_by('id') để chạy tuần tự không trùng lặp
            movies = Movie.objects.filter(imdb_rating=0.0).order_by('id')[:100]
            
            if not movies.exists():
                self.stdout.write(self.style.SUCCESS("✅ TẤT CẢ PHIM ĐÃ ĐƯỢC ĐỒNG BỘ XONG!"))
                break

            total_remain = Movie.objects.filter(imdb_rating=0.0).count()
            self.stdout.write(self.style.WARNING(f"🚀 Còn {total_remain} phim. Đang xử lý 100 phim tiếp theo..."))
            
            # Sử dụng ThreadPoolExecutor để tăng tốc độ gọi API
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(self.update_single_movie, movies)
            
            # Nghỉ 1 giây để tránh Rate Limit của TMDB và giải phóng RAM
            gc.collect()
            time.sleep(1)

    def update_single_movie(self, movie):
        try:
            # 1. Làm sạch tên truy vấn: Xóa năm (2024), bản cam, v.v.
            search_query = re.sub(r'\s*\(\d{4}\)', '', movie.origin_name).strip()
            
            endpoint = "tv" if movie.is_series else "movie"
            search_url = f"https://api.themoviedb.org/3/search/{endpoint}"
            
            params = {
                'api_key': self.TMDB_API_KEY,
                'query': search_query,
                'language': 'vi-VN',
            }

            response = self.session.get(search_url, params=params, timeout=10)
            
            # Xử lý khi bị TMDB chặn do gọi quá nhanh
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 5))
                time.sleep(retry_after)
                return

            data = response.json()
            if data.get('results'):
                best_match = data['results'][0]
                tmdb_id = best_match['id']

                # Lấy chi tiết để có Genres và Countries chuẩn
                detail_url = f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}"
                detail_res = self.session.get(detail_url, params={'api_key': self.TMDB_API_KEY, 'language': 'vi-VN'}).json()

                # --- TỐI ƯU HÓA GENRES (Để lọc phim mượt hơn) ---
                tmdb_genres = detail_res.get('genres', [])
                if tmdb_genres:
                    genre_list = [f"{g['name']}, {g['name'].lower().replace(' ', '-')}" for g in tmdb_genres]
                    movie.genres = ", ".join(genre_list)
                else:
                    # Fallback nếu TMDB không có thể loại tiếng Việt
                    old_gs = [g.strip() for g in movie.genres.split(',') if g.strip()]
                    movie.genres = ", ".join([f"{g}, {g.lower().replace(' ', '-')}" for g in old_gs])

                # --- TỐI ƯU QUỐC GIA ---
                countries = detail_res.get('production_countries', [])
                if countries:
                    c_list = [f"{c['name']}, {c['name'].lower().replace(' ', '-')}" for c in countries]
                    movie.country = ", ".join(c_list)

                # --- CẬP NHẬT ẢNH CHẤT LƯỢNG CAO ---
                movie.description = best_match.get('overview') or movie.description
                if best_match.get('poster_path'):
                    movie.poster_url = f"https://image.tmdb.org/t/p/w500{best_match['poster_path']}"
                if best_match.get('backdrop_path'):
                    movie.thumb_url = f"https://image.tmdb.org/t/p/w780{best_match['backdrop_path']}"
                
                # --- ĐÁNH DẤU HOÀN THÀNH & ĐẨY LÊN TRANG CHỦ ---
                rating = best_match.get('vote_average', 0)
                movie.imdb_rating = rating if rating > 0 else 0.1
                movie.updated_at = timezone.now() # Đẩy lên đầu trang chủ ngay lập tức
                movie.save()
                
                self.stdout.write(self.style.SUCCESS(f"✔ Đã nâng cấp: {movie.title}"))
            else:
                # Nếu không thấy trên TMDB: Vẫn chuẩn hóa genres cũ để bộ lọc không lỗi
                if movie.genres:
                    old_gs = [g.strip() for g in movie.genres.split(',') if g.strip()]
                    movie.genres = ", ".join([f"{g}, {g.lower().replace(' ', '-')}" for g in old_gs])
                
                # Đánh dấu 0.01 để script không quét lại phim này ở vòng lặp sau
                movie.imdb_rating = 0.01 
                movie.save()
                self.stdout.write(self.style.ERROR(f"✘ Không thấy trên TMDB: {movie.title}"))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ Lỗi tại {movie.title}: {str(e)}"))