import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from main.models import Movie

class Command(BaseCommand):
    help = 'Cập nhật TMDB và tối ưu hóa dữ liệu phim (Chạy nối tiếp)'

    TMDB_API_KEY = '640d361bde1790dea88b0c75524307d4'

    def handle(self, *args, **options):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        while True:
            # Chỉ lấy những phim chưa được tối ưu (rating vẫn là 0.0)
            movies = Movie.objects.filter(imdb_rating=0.0)[:100]
            
            if not movies.exists():
                self.stdout.write(self.style.SUCCESS("✅ TẤT CẢ 22,646 PHIM ĐÃ ĐƯỢC ĐỒNG BỘ XONG!"))
                break

            count = Movie.objects.filter(imdb_rating=0.0).count()
            self.stdout.write(self.style.WARNING(f"🚀 Còn khoảng {count} phim. Đang xử lý 100 phim tiếp theo..."))
            
            # Tăng workers lên 10 để chạy cho nhanh vì data của ông quá lớn
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(self.update_single_movie, movies)
            
            # Nghỉ 1 giây sau mỗi batch 100 phim để tránh bị TMDB chặn IP
            time.sleep(1)

    def update_single_movie(self, movie):
        try:
            # Làm sạch tên truy vấn (Bỏ bớt năm nếu dính trong tên gốc)
            search_query = re.sub(r'\s*\(\d{4}\)', '', movie.origin_name).strip()
            
            is_tv = movie.is_series
            endpoint = "tv" if is_tv else "movie"
            search_url = f"https://api.themoviedb.org/3/search/{endpoint}"
            
            params = {
                'api_key': self.TMDB_API_KEY,
                'query': search_query,
                'language': 'vi-VN',
            }

            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 429:
                time.sleep(5)
                return

            data = response.json()
            if data.get('results'):
                best_match = data['results'][0]
                tmdb_id = best_match['id']

                # Lấy chi tiết để có dữ liệu sâu hơn
                detail_url = f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}"
                detail_res = self.session.get(detail_url, params={'api_key': self.TMDB_API_KEY, 'language': 'vi-VN'}).json()

                # --- TỐI ƯU HÓA GENRES ---
                tmdb_genres = detail_res.get('genres', [])
                if tmdb_genres:
                    genre_list = [f"{g['name']}, {g['name'].lower().replace(' ', '-')}" for g in tmdb_genres]
                    movie.genres = ", ".join(genre_list)
                else:
                    # Fix fallback nếu TMDB không có genres
                    old_gs = [g.strip() for g in movie.genres.split(',') if g.strip()]
                    movie.genres = ", ".join([f"{g}, {g.lower().replace(' ', '-')}" for g in old_gs])

                # --- TỐI ƯU QUỐC GIA ---
                countries = detail_res.get('production_countries', [])
                if countries:
                    c_list = [f"{c['name']}, {c['name'].lower().replace(' ', '-')}" for c in countries]
                    movie.country = ", ".join(c_list)

                # Cập nhật thông tin hình ảnh và mô tả chất lượng cao
                movie.description = best_match.get('overview') or movie.description
                if best_match.get('poster_path'):
                    movie.poster_url = f"https://image.tmdb.org/t/p/w500{best_match['poster_path']}"
                if best_match.get('backdrop_path'):
                    movie.thumb_url = f"https://image.tmdb.org/t/p/w780{best_match['backdrop_path']}"
                
                # Cập nhật rating TMDB (để làm mốc đánh dấu đã xong)
                rating = best_match.get('vote_average', 0)
                movie.imdb_rating = rating if rating > 0 else 0.1
                movie.save()
                
                self.stdout.write(self.style.SUCCESS(f"✔ Đã tối ưu: {movie.title}"))
            else:
                # Nếu không tìm thấy trên TMDB: Vẫn tối ưu genres cũ để Filter hoạt động
                if movie.genres:
                    old_gs = [g.strip() for g in movie.genres.split(',') if g.strip()]
                    movie.genres = ", ".join([f"{g}, {g.lower().replace(' ', '-')}" for g in old_gs])
                
                # Đánh dấu rating cực thấp để không lặp lại phim này nữa
                movie.imdb_rating = 0.01 
                movie.save()
                self.stdout.write(self.style.ERROR(f"✘ TMDB không thấy - Đã fix genres: {movie.title}"))

        except Exception as e:
            self.stdout.write(f"⚠️ Lỗi tại phim {movie.title}: {str(e)}")
            pass