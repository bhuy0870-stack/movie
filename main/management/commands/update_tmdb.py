import requests
import time
import re
import gc
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Movie

class Command(BaseCommand):
    help = 'Nâng cấp dữ liệu phim từ TMDB (Tối ưu cho Render)'

    TMDB_API_KEY = '640d361bde1790dea88b0c75524307d4'

    def handle(self, *args, **options):
        self.session = requests.Session()
        # Giảm số lượng phim mỗi đợt xuống 50 để tránh treo memory trên Render Free
        BATCH_SIZE = 50 

        self.stdout.write(self.style.SUCCESS("🚀 BẮT ĐẦU ĐỒNG BỘ TMDB..."))

        while True:
            # Lấy phim có imdb_rating = 0.0 (chưa xử lý)
            movies = Movie.objects.filter(imdb_rating=0.0).order_by('id')[:BATCH_SIZE]
            
            if not movies.exists():
                self.stdout.write(self.style.SUCCESS("✅ TẤT CẢ PHIM ĐÃ ĐƯỢC ĐỒNG BỘ XONG!"))
                break

            total_remain = Movie.objects.filter(imdb_rating=0.0).count()
            self.stdout.write(self.style.WARNING(f"🔄 Còn {total_remain} phim. Đang xử lý {BATCH_SIZE} phim..."))
            
            # Giảm max_workers xuống 5 để Render không bị tràn CPU/RAM
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(self.update_single_movie, movies)
            
            # Giải phóng bộ nhớ triệt để sau mỗi batch
            gc.collect()
            # Nghỉ một chút để TMDB không khóa API Key của bạn
            time.sleep(2)

    def update_single_movie(self, movie):
        try:
            # 1. Làm sạch tên phim: Xóa các ký tự đặc biệt và năm để TMDB tìm chính xác hơn
            clean_name = re.sub(r'\s*\(\d{4}\)', '', movie.origin_name) # Xóa (2024)
            clean_name = re.sub(r'(?i)vietsub|thuyết minh|lồng tiếng|bản cam', '', clean_name).strip()
            
            endpoint = "tv" if movie.is_series else "movie"
            search_url = f"https://api.themoviedb.org/3/search/{endpoint}"
            
            params = {
                'api_key': self.TMDB_API_KEY,
                'query': clean_name,
                'language': 'vi-VN',
            }

            response = self.session.get(search_url, params=params, timeout=10)
            
            if response.status_code == 429: # Rate Limit
                time.sleep(5)
                return

            data = response.json()
            if data.get('results'):
                best_match = data['results'][0]
                tmdb_id = best_match['id']

                # 2. Lấy chi tiết để lấy Thể loại và Quốc gia chuẩn
                detail_url = f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}"
                detail_res = self.session.get(detail_url, params={'api_key': self.TMDB_API_KEY, 'language': 'vi-VN'}, timeout=10).json()

                # --- TỐI ƯU HÓA THỂ LOẠI (Hỗ trợ Search/Filter) ---
                tmdb_genres = detail_res.get('genres', [])
                if tmdb_genres:
                    # Lưu cả tên Tiếng Việt và slug để bộ lọc (base.html) hoạt động
                    g_list = []
                    for g in tmdb_genres:
                        name = g['name']
                        slug = name.lower().replace(' ', '-')
                        g_list.append(f"{name}, {slug}")
                    movie.genres = ", ".join(g_list)

                # --- TỐI ƯU QUỐC GIA ---
                countries = detail_res.get('production_countries', [])
                if countries:
                    c_list = [f"{c['name']}, {c['name'].lower().replace(' ', '-')}" for c in countries]
                    movie.country = ", ".join(c_list)

                # --- CẬP NHẬT THÔNG TIN & ẢNH ---
                movie.description = best_match.get('overview') or movie.description
                if best_match.get('poster_path'):
                    movie.poster_url = f"https://image.tmdb.org/t/p/w500{best_match['poster_path']}"
                if best_match.get('backdrop_path'):
                    movie.thumb_url = f"https://image.tmdb.org/t/p/w780{best_match['backdrop_path']}"
                
                # --- ĐÁNH DẤU HOÀN THÀNH ---
                rating = best_match.get('vote_average', 0)
                movie.imdb_rating = rating if rating > 0 else 0.1
                # Không ép updated_at = now() ở đây để tránh làm xáo trộn phim mới cào
                movie.save()
                
                self.stdout.write(self.style.SUCCESS(f"✔ TMDB OK: {movie.title} ({rating})"))
            else:
                # Nếu không tìm thấy: Đánh dấu để không quét lại lần sau
                movie.imdb_rating = 0.01 
                movie.save()
                self.stdout.write(self.style.ERROR(f"✘ TMDB No Result: {movie.title}"))

        except Exception as e:
            # Ghi log lỗi nhưng không làm dừng script
            self.stdout.write(self.style.WARNING(f"⚠️ Error {movie.title}: {str(e)}"))