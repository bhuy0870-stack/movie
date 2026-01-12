from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField

# --- 1. HỆ THỐNG THÀNH TÍCH ---
class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField() # Sửa thành TextField cho an toàn
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

# --- 2. HỆ THỐNG PHIM (Tối ưu chống lỗi 22k phim) ---

class Movie(models.Model):
    # Slug dùng làm ID duy nhất
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    title = models.CharField(max_length=255)
    origin_name = models.CharField(max_length=255, blank=True, null=True)
    
    # CHỖ NÀY QUAN TRỌNG: Chuyển hết sang TextField để không giới hạn độ dài
    description = models.TextField(blank=True, null=True)
    release_date = models.CharField(max_length=100, null=True, blank=True) 
    
    # Poster và Thumb thường rất dài nếu là link từ TMDB/Ophim
    poster_url = models.TextField(blank=True, null=True) 
    thumb_url = models.TextField(blank=True, null=True)
    
    # Director và Cast của OPhim trả về đôi khi cực kỳ dài
    director = models.TextField(blank=True, null=True)
    cast = models.TextField(blank=True, null=True)
    
    # Genres và Country chứa cả tên và slug nên cần TextField
    genres = models.TextField(blank=True, null=True) 
    country = models.TextField(blank=True, null=True)
    
    # Phân loại phim
    is_series = models.BooleanField(default=False) 
    total_episodes = models.CharField(max_length=100, default="1")
    current_episode = models.CharField(max_length=100, default="Full")
    
    # Rating & Settings
    imdb_rating = models.FloatField(default=0.0)
    age_limit = models.IntegerField(default=0)
    
    # Cấu hình Bunny
    bunny_library_id = models.CharField(max_length=100, default="577395") 

    def __str__(self):
        return self.title

class Episode(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='episodes')
    server_name = models.CharField(max_length=255, default="Vietsub #1")
    episode_name = models.CharField(max_length=255)
    episode_slug = models.SlugField(max_length=255)
    
    # Link phim .m3u8 thường rất dài và ngoằn ngoèo
    link_ophim = models.TextField(help_text="Link .m3u8 từ Ophim")
    link_bunny_id = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.movie.title} - {self.episode_name}"

# --- 3. TƯƠNG TÁC NGƯỜI DÙNG ---
class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    rating = models.IntegerField(default=5)
    sentiment_label = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_reviews', blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"
    
    @property
    def total_likes(self):
        return self.likes.count()
    
class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist_items')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')

# --- 4. THÔNG TIN MỞ RỘNG NGƯỜI DÙNG ---
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = CloudinaryField('image', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, null=True)

# --- 5. SIGNALS ---
@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance) # Dùng get_or_create cho chắc chắn
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()


class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_history')
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE) # Giả định model Phim của bạn tên là Movie
    watched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-watched_at']
        unique_together = ('user', 'movie') # Mỗi phim chỉ xuất hiện 1 lần trong lịch sử 1 người

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"