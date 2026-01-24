from django.contrib.sitemaps import Sitemap
from .models import Movie

class MovieSitemap(Sitemap):
    changefreq = "daily"  # Báo Google: "Web tôi có phim mới mỗi ngày"
    priority = 0.9        # Độ ưu tiên cao (thang điểm 1.0)

    def items(self):
        # Lấy danh sách tất cả phim
        return Movie.objects.all().order_by('-id')

    def location(self, item):
        # Trả về đường dẫn của từng phim
        return f"/movie/{item.slug}/"