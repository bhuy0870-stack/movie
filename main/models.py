from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField
from django.db.models.functions import Cast
from django.db.models import IntegerField

# --- 1. HỆ THỐNG THÀNH TÍCH ---
class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField() 
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

# --- 2. HỆ THỐNG PHIM ---
class Movie(models.Model):
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    title = models.CharField(max_length=255)
    origin_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    release_date = models.CharField(max_length=100, null=True, blank=True) 
    poster_url = models.TextField(blank=True, null=True) 
    thumb_url = models.TextField(blank=True, null=True)
    director = models.TextField(blank=True, null=True)
    cast = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    genres = models.TextField(blank=True, null=True) 
    country = models.TextField(blank=True, null=True)
    is_series = models.BooleanField(default=False) 
    total_episodes = models.CharField(max_length=100, default="1")
    current_episode = models.CharField(max_length=100, default="Full")
    imdb_rating = models.FloatField(default=0.0)
    age_limit = models.IntegerField(default=0)
    bunny_library_id = models.CharField(max_length=100, default="577395") 

    def __str__(self):
        return self.title

class Episode(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='episodes')
    server_name = models.CharField(max_length=255, default="Vietsub #1")
    episode_name = models.CharField(max_length=255)
    episode_slug = models.SlugField(max_length=255)
    link_ophim = models.TextField(help_text="Link .m3u8 từ Ophim")
    link_bunny_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Sửa lỗi sắp xếp 1, 10, 2 bằng cách ép kiểu ngay trong Meta (nếu DB hỗ trợ)
        # Hoặc dùng logic sắp xếp trong Views (Xem phần views bên dưới)
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
    birth_date = models.DateField(null=True, blank=True)

# --- 5. LỊCH SỬ XEM ---
class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_history')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    watched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-watched_at']
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"

# --- 6. SIGNALS ---
@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()