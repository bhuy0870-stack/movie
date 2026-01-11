from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- 1. HỆ THỐNG THÀNH TÍCH ---
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

# --- 2. HỆ THỐNG PHIM (Tối ưu cho Ophim & Bunny) ---

class Movie(models.Model):
    # Dùng Slug của Ophim làm ID duy nhất để tránh trùng lặp khi cào dữ liệu
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    title = models.CharField(max_length=255)
    origin_name = models.CharField(max_length=255, blank=True, null=True) # Tên tiếng Anh/Gốc
    description = models.TextField(blank=True, null=True)
    release_date = models.CharField(max_length=50, null=True, blank=True) # Ophim trả về năm (String)
    poster_url = models.URLField(max_length=500)
    thumb_url = models.URLField(max_length=500, blank=True, null=True) # Ảnh ngang (Thumbnail)
    
    # Thông tin bổ sung - Tăng max_length để tránh lỗi khi chuỗi OPhim trả về quá dài
    director = models.CharField(max_length=500, blank=True, null=True)
    cast = models.TextField(blank=True, null=True)
    genres = models.CharField(max_length=500, blank=True) # Chứa chuỗi: "Hành động, hanh-dong, ..."
    country = models.CharField(max_length=255, default="Đang cập nhật")
    
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
    episode_slug = models.SlugField(max_length=255)
    
    # Link phim
    link_ophim = models.URLField(max_length=1000, help_text="Link .m3u8 từ Ophim")
    link_bunny_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID Video trên Bunny (nếu có)")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id'] # Sắp xếp theo thứ tự thêm vào (ID tăng dần)

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

    def __str__(self):
        return f"{self.user.username} đánh giá {self.movie.title}"

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist_items')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')

# --- 4. THÔNG TIN MỞ RỘNG NGƯỜI DÙNG ---
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(
        upload_to='avatars/', 
        null=True, 
        blank=True, 
        help_text="Ảnh đại diện người dùng"
    )
    bio = models.TextField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return f"Profile of {self.user.username}"

# --- 5. SIGNALS (Tự động tạo Profile) ---
@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # Kiểm tra nếu profile đã tồn tại mới save để tránh lỗi hệ thống
        if hasattr(instance, 'profile'):
            instance.profile.save()