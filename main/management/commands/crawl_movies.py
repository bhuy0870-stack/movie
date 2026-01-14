import requests
import time
import gc
import re
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone  # Thêm để cập nhật thời gian thực
from main.models import Movie, Episode

class Command(BaseCommand):
    help = 'Cào phim OPhim chuyên nghiệp và tự động đẩy phim mới lên đầu'

    OPHIM_API_URL = "https://ophim1.com/danh-sach/phim-moi-cap-nhat"

    def add_arguments(self, parser):
        parser.add_argument('--start', type=int, default=1, help='Trang bắt đầu')
        parser.add_argument('--end', type=int, default=3, help='Trang kết thúc (Mặc định cào 3 trang mới nhất)')

    def handle(self, *args, **options):
        start_page = options['start']
        end_page = options['end']
        
        self.stdout.write(self.style.SUCCESS(f'🚀 BẮT ĐẦU CÀO: Trang {start_page} -> {end_page}'))
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Tăng lên 10 workers để chạy nhanh hơn trên môi trường GitHub Actions
        with ThreadPoolExecutor(max_workers=10) as executor:
            pages = range(start_page, end_page + 1)
            executor.map(self.process_page, pages)

        self.stdout.write(self.style.SUCCESS(f'✅ HOÀN THÀNH CẬP NHẬT PHIM!'))

    def process_page(self, page):
        try:
            url = f"{self.OPHIM_API_URL}?page={page}"
            res = self.session.get(url, timeout=15).json()
            items = res.get('items', [])
            
            for item in items:
                self.process_movie(item['slug'])
            
            self.stdout.write(self.style.MIGRATE_LABEL(f"📌 Xong trang {page}"))
            gc.collect() 
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Lỗi trang {page}: {e}"))

    def process_movie(self, slug):
        try:
            res = self.session.get(f"https://ophim1.com/phim/{slug}", timeout=15).json()
            m = res['movie']
            ep_data = res.get('episodes', [])

            valid_eps = []
            for server in ep_data:
                server_name = server['server_name']
                for item in server['server_data']:
                    if item.get('link_m3u8'):
                        valid_eps.append({'server': server_name, 'data': item})

            if not valid_eps:
                return

            # --- TỐI ƯU HÓA GENRES (Thể loại) ---
            genre_list = []
            for cat in m.get('category', []):
                genre_list.append(cat['name'])
                genre_list.append(cat['slug'])
            combined_genres = ", ".join(genre_list)

            # --- TỐI ƯU HÓA COUNTRY (Quốc gia) ---
            country_list = []
            for c in m.get('country', []):
                country_list.append(c['name'])
                country_list.append(c['slug'])
            combined_countries = ", ".join(country_list)

            # --- XỬ LÝ LINK ẢNH (Phòng trường hợp link thiếu https) ---
            def fix_url(url):
                if url and url.startswith('//'): return f"https:{url}"
                return url

            with transaction.atomic():
                # update_or_create sẽ kích hoạt auto_now=True của trường updated_at
                movie, created = Movie.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'title': m['name'],
                        'origin_name': m['origin_name'],
                        'description': m['content'],
                        'poster_url': fix_url(m['thumb_url']),
                        'thumb_url': fix_url(m['poster_url']),
                        'release_date': m['year'],
                        'is_series': m['type'] == 'series',
                        'total_episodes': m['episode_total'],
                        'current_episode': m['episode_current'],
                        'country': combined_countries,
                        'genres': combined_genres,
                        'updated_at': timezone.now(), # ÉP BUỘC CẬP NHẬT THỜI GIAN ĐỂ LÊN ĐẦU TRANG
                    }
                )

                for item in valid_eps:
                    Episode.objects.update_or_create(
                        movie=movie,
                        episode_slug=item['data']['slug'],
                        server_name=item['server'],
                        defaults={
                            'episode_name': item['data']['name'],
                            'link_ophim': item['data']['link_m3u8'],
                        }
                    )
            
            status = "Mới" if created else "Cập nhật"
            self.stdout.write(self.style.SUCCESS(f"✔ {status}: {movie.title}"))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ Lỗi phim {slug}: {e}"))