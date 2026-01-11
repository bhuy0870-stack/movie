import requests
import time
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from main.models import Movie, Episode

class Command(BaseCommand):
    help = 'Crawl phim tùy chỉnh phạm vi trang - Chỉ lấy M3U8'

    TMDB_API_KEY = '640d361bde1790dea88b0c75524307d4'
    OPHIM_API_URL = "https://ophim1.com/danh-sach/phim-moi-cap-nhat"

    def add_arguments(self, parser):
        # Thêm lựa chọn trang bắt đầu và kết thúc
        parser.add_argument('--start', type=int, default=1, help='Trang bắt đầu')
        parser.add_argument('--end', type=int, default=100, help='Trang kết thúc')

    def handle(self, *args, **options):
        start_page = options['start']
        end_page = options['end']
        
        self.stdout.write(self.style.SUCCESS(f'🚀 BẮT ĐẦU CÀO TỪ TRANG {start_page} ĐẾN {end_page}...'))
        
        start_time = time.time()
        self.session = requests.Session()
        
        # Chạy đa luồng
        with ThreadPoolExecutor(max_workers=25) as executor:
            pages = range(start_page, end_page + 1)
            executor.map(self.process_page, pages)

        total_time = round(time.time() - start_time, 2)
        self.stdout.write(self.style.SUCCESS(f'✅ HOÀN THÀNH ĐỢT CÀO! Tổng thời gian: {total_time} giây'))

    def process_page(self, page):
        try:
            url = f"{self.OPHIM_API_URL}?page={page}"
            res = self.session.get(url, timeout=10).json()
            items = res.get('items', [])
            for item in items:
                self.process_movie(item['slug'])
            self.stdout.write(self.style.MIGRATE_LABEL(f"📌 Xong trang {page}"))
        except:
            pass

    def process_movie(self, slug):
        try:
            ophim_res = self.session.get(f"https://ophim1.com/phim/{slug}", timeout=10).json()
            m = ophim_res['movie']
            episodes_data = ophim_res.get('episodes', [])

            valid_episodes = []
            has_m3u8 = False
            for server in episodes_data:
                for ep in server['server_data']:
                    if ep.get('link_m3u8') and ep['link_m3u8'].strip().lower().endswith('.m3u8'):
                        has_m3u8 = True
                        valid_episodes.append({'server': server['server_name'], 'ep': ep})

            if not has_m3u8:
                return 

            tmdb_data = self.get_tmdb_info(m['origin_name'], m['year'])
            
            movie, _ = Movie.objects.update_or_create(
                slug=slug,
                defaults={
                    'title': m['name'],
                    'origin_name': m['origin_name'],
                    'description': tmdb_data.get('overview') or m['content'],
                    'poster_url': f"https://image.tmdb.org/t/p/w500{tmdb_data.get('poster_path')}" if tmdb_data.get('poster_path') else m['thumb_url'],
                    'thumb_url': f"https://image.tmdb.org/t/p/w500{tmdb_data.get('backdrop_path')}" if tmdb_data.get('backdrop_path') else m['poster_url'],
                    'release_date': m['year'],
                    'imdb_rating': tmdb_data.get('vote_average') or 0.0,
                    'is_series': m['type'] == 'series',
                    'total_episodes': m['episode_total'],
                    'current_episode': m['episode_current'],
                    'country': m['country'][0]['name'] if m['country'] else "Âu Mỹ",
                    'genres': ", ".join([cat['name'] for cat in m.get('category', [])]),
                }
            )

            for data in valid_episodes:
                Episode.objects.update_or_create(
                    movie=movie,
                    episode_slug=data['ep']['slug'],
                    defaults={
                        'server_name': data['server'],
                        'episode_name': data['ep']['name'],
                        'link_ophim': data['ep']['link_m3u8'],
                    }
                )
        except:
            pass

    def get_tmdb_info(self, title, year):
        try:
            url = f"https://api.themoviedb.org/3/search/movie?api_key={self.TMDB_API_KEY}&query={title}&language=vi-VN&year={year}"
            res = self.session.get(url, timeout=5).json()
            return res['results'][0] if res.get('results') else {}
        except:
            return {}