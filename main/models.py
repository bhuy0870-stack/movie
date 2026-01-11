from django.db import models
from django.contrib.auth.models import User

# --- Hệ thống Thành tích (Giữ nguyên) ---
class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    icon_class = models.CharField(max_length=50, help_text="Sử dụng FontAwesome, ví dụ: fas fa-moon")
    color = models.CharField(max_length=20, default="#ffcc00")

    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    date_unlocked = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'achievement')

# --- Hệ thống Phim (Tối ưu cho Ophim & Bunny) ---
class Movie(models.Model):
    # Dùng Slug của Ophim làm ID duy nhất để tránh trùng lặp khi cào dữ liệu
    slug = models.SlugField(unique=True, max_length=255, help_text="Slug từ Ophim (ví dụ: spider-man-no-way-home)")
    api_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    title = models.CharField(max_length=255)
    origin_name = models.CharField(max_length=255, blank=True, null=True) # Tên tiếng Anh/Gốc
    description = models.TextField(blank=True, null=True)
    release_date = models.CharField(max_length=50, null=True, blank=True) # Ophim thường trả về năm (String)
    poster_url = models.URLField(max_length=500)
    thumb_url = models.URLField(max_length=500, blank=True, null=True) # Ảnh ngang (Thumbnail)
    
    # Thông tin bổ sung
    director = models.CharField(max_length=255, blank=True, null=True)
    cast = models.TextField(blank=True, null=True)
    genres = models.CharField(max_length=255, blank=True) 
    country = models.CharField(max_length=100, default="Đang cập nhật")
    
    # Phân loại phim
    is_series = models.BooleanField(default=False) 
    total_episodes = models.CharField(max_length=50, default="1")
    current_episode = models.CharField(max_length=50, default="Full", help_text="Ví dụ: Tập 5 hoặc Hoàn tất")
    
    # Rating & Settings
    imdb_rating = models.FloatField(default=0.0)
    age_limit = models.IntegerField(default=0)
    
    # Cấu hình Bunny chung cho cả bộ phim
    bunny_library_id = models.CharField(max_length=50, default="577395") 

    def __str__(self):
        return self.title

class Episode(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='episodes')
    server_name = models.CharField(max_length=100, default="Vietsub #1")
    episode_name = models.CharField(max_length=100, help_text="Ví dụ: Tập 01, Full")
    episode_slug = models.SlugField(max_length=100)
    
    # Link phim
    link_ophim = models.URLField(max_length=1000, help_text="Link .m3u8 từ Ophim")
    link_bunny_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID Video trên Bunny (nếu có)")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id'] # Sắp xếp theo thứ tự thêm vào

    def __str__(self):
        return f"{self.movie.title} - {self.episode_name}"

# --- Tương tác Người dùng ---
class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    rating = models.IntegerField(default=5)
    sentiment_label = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_reviews', blank=True)

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')