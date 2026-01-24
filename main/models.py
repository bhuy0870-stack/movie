from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField

# --- 0. TÍCH HỢP TRÍ TUỆ NHÂN TẠO (AI) ---
# Thử tải model PhoBERT (Dùng try/except để tránh sập web nếu thiếu RAM)
try:
    from transformers import pipeline
    # Model này nhẹ (~400MB) chuyên dùng cho tiếng Việt
    sentiment_analyzer = pipeline("sentiment-analysis", model="wonrax/phobert-base-vietnamese-sentiment")
    AI_AVAILABLE = True
    print("✅ Đã tải xong Model AI phân tích cảm xúc!")
except Exception as e:
    AI_AVAILABLE = False
    print(f"⚠️ Không tải được AI (Web vẫn chạy bình thường): {e}")

# --- 1. HỆ THỐNG THÀNH TÍCH (GAMIFICATION) ---
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
    # Lưu thể loại dạng chuỗi text (Ví dụ: "Hành động, Phiêu lưu")
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
        ordering = ['id']

    def __str__(self):
        return f"{self.movie.title} - {self.episode_name}"

# --- 3. TƯƠNG TÁC NGƯỜI DÙNG (REVIEW + AI) ---
class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews') # related_name='reviews' quan trọng cho Admin Dashboard
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    rating = models.IntegerField(default=10)
    
    # Kết quả phân tích AI
    sentiment_label = models.CharField(max_length=50, null=True, blank=True) # POS (Tích cực), NEG (Tiêu cực)
    sentiment_score = models.FloatField(default=0.0) # Độ tin cậy (0.0 - 1.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_reviews', blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"
    
    @property
    def total_likes(self):
        return self.likes.count()

    # Tự động gọi AI khi lưu bình luận
    def save(self, *args, **kwargs):
        # Nếu chưa có nhãn cảm xúc và AI đang hoạt động
        if not self.sentiment_label and AI_AVAILABLE and self.comment:
            try:
                # Cắt ngắn comment nếu quá dài (AI chỉ đọc được khoảng 256 từ)
                short_comment = self.comment[:500]
                result = sentiment_analyzer(short_comment)[0]
                self.sentiment_label = result['label'] # POS hoặc NEG
                self.sentiment_score = round(result['score'], 4)
            except Exception as e:
                print(f"Lỗi phân tích AI: {e}")
        
        super().save(*args, **kwargs)

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

    def __str__(self):
        return f"Profile của {self.user.username}"

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

# --- 6. SIGNALS (Tự động tạo Profile) ---
@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
    else:
        # Chỉ save nếu profile đã tồn tại để tránh lỗi
        if hasattr(instance, 'profile'):
            instance.profile.save()