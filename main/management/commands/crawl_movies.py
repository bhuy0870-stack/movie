import requests
import time
import gc
import re
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from main.models import Movie, Episode
from webpush import send_group_notification

class Command(BaseCommand):
    help = 'Cào phim OPhim chuyên nghiệp và tự động đẩy phim mới lên đầu'

    OPHIM_API_URL = "https://ophim1.com/danh-sach/phim-moi-cap-nhat"

    def add_arguments(self, parser):
        parser.add_argument('--start', type=int, default=1, help='Trang bắt đầu')
        parser.add_argument('--end', type=int, default=3, help='Trang kết thúc')

    def handle(self, *args, **options):
        start_page = options['start']
        end_page = options['end']
        
        self.stdout.write(self.style.SUCCESS(f'🚀 BẮT ĐẦU CÀO: Trang {start_page} -> {end_page}'))
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        with ThreadPoolExecutor(max_workers=3) as executor:
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

            # --- TỐI ƯU GENRES & COUNTRY ---
            combined_genres = ", ".join([cat['name'] for cat in m.get('category', [])] + [cat['slug'] for cat in m.get('category', [])])
            combined_countries = ", ".join([c['name'] for c in m.get('country', [])] + [c['slug'] for c in m.get('country', [])])

            def fix_url(url):
                if url and url.startswith('//'): return f"https:{url}"
                return url

            with transaction.atomic():
                # 1. Tìm phim cũ dựa trên slug (Tránh lỗi Duplicate ID)
                movie = Movie.objects.filter(slug=slug).first()
                has_new_episode = False
                created = False

                movie_data = {
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
                    'updated_at': timezone.now(), # Đẩy lên đầu trang
                }

                if movie:
                    if movie.current_episode != m['episode_current']:
                        has_new_episode = True
                    # Update phim đã có
                    for key, value in movie_data.items():
                        setattr(movie, key, value)
                    movie.save()
                else:
                    # Tạo phim mới hoàn toàn (Để Postgres tự cấp ID mới nhất)
                    movie = Movie.objects.create(slug=slug, **movie_data)
                    created = True

                # 2. Cập nhật tập phim
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
            
            # --- GỬI THÔNG BÁO ---
            if created or has_new_episode:
                notification_title = "🎬 Phim mới" if created else "🔔 Tập mới"
                payload = {
                    "title": f"{notification_title}: {movie.title}",
                    "body": f"Trạng thái: {movie.current_episode}. Xem ngay tại BQH MOVIE!",
                    "url": f"https://movie-yu48.onrender.com/phim/{movie.slug}/"
                }
                try:
                    send_group_notification(group_name="phim-moi", payload=payload)
                except:
                    pass

            status = "Mới" if created else "Cập nhật"
            self.stdout.write(self.style.SUCCESS(f"✔ {status}: {movie.title}"))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ Lỗi phim {slug}: {e}"))