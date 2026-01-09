from django.db import models
from django.contrib.auth.models import User

class Movie(models.Model):
    api_id = models.IntegerField(unique=True, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    release_date = models.DateField(null=True, blank=True)
    poster_url = models.URLField()
    trailer_url = models.URLField(null=True, blank=True)
    director = models.CharField(max_length=200, blank=True, null=True)
    cast = models.TextField(blank=True, null=True)
    genres = models.CharField(max_length=255, blank=True) 
    age_limit = models.IntegerField(default=0)
    # movie_url nên để trống nếu là phim bộ, hoặc dùng làm link tập 1 cho phim lẻ
    movie_url = models.URLField(max_length=500, blank=True, null=True)
    country = models.CharField(max_length=100, default="Âu Mỹ")
    is_series = models.BooleanField(default=False) 
    total_episodes = models.CharField(max_length=50, default="1", help_text="Ví dụ: 12 hoặc Hoàn thành (12/12)")
    imdb_rating = models.FloatField(default=0.0) # Thêm vào để đồng bộ với admin

    def __str__(self):
        return self.title

# BẢNG MỚI: Quản lý từng tập phim
class Episode(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='episodes')
    episode_number = models.IntegerField(default=1)
    title = models.CharField(max_length=255, blank=True, help_text="Tên tập (nếu có)")
    video_url = models.URLField(max_length=500) # Link phim của riêng tập này
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['episode_number']

    def __str__(self):
        return f"{self.movie.title} - Tập {self.episode_number}"



class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    rating = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    sentiment_score = models.FloatField(default=0.0)
    sentiment_label = models.CharField(max_length=50, blank=True, null=True)
    likes = models.ManyToManyField(User, related_name='liked_reviews', blank=True)    
    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"
    
    # main/models.py
class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie') # Tránh lưu trùng 1 bộ phim nhiều lần