from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Achievement, UserAchievement, Review, Watchlist
from django.db.models import Count

# --- HELPER FUNCTION TẶNG HUY HIỆU ---
def award_badge(user, name, description, icon, color):
    achievement, _ = Achievement.objects.get_or_create(
        name=name,
        defaults={'description': description, 'icon_class': icon, 'color': color}
    )
    UserAchievement.objects.get_or_create(user=user, achievement=achievement)

# --- 1. HỆ THỐNG HUY HIỆU KHI ĐĂNG KÝ & ĐÓNG GÓP ---
@receiver(post_save, sender=User)
def welcome_and_donor_badges(sender, instance, created, **kwargs):
    if created:
        # 1. Huy hiệu: Thành Viên Mới
        award_badge(instance, 'Thành Viên Mới', 'Gia nhập cộng đồng xem phim', 'fas fa-user-plus', '#2ecc71')

# --- 2. HỆ THỐNG HUY HIỆU BÌNH LUẬN (Review) ---
@receiver(post_save, sender=Review)
def review_achievements(sender, instance, created, **kwargs):
    if created:
        user = instance.user
        review_count = Review.objects.filter(user=user).count()
        
        # 2. Huy hiệu: Tập Sự (1 bình luận)
        if review_count >= 1:
            award_badge(user, 'Tập Sự', 'Để lại bình luận đầu tiên', 'fas fa-pen-fancy', '#95a5a6')
        
        # 3. Huy hiệu: Bình Luận Viên (5 bình luận)
        if review_count >= 5:
            award_badge(user, 'Bình Luận Viên', 'Đóng góp 5 ý kiến cho phim', 'fas fa-comment-dots', '#e91e63')
            
        # 4. Huy hiệu: Thánh Phê Bình (20 bình luận)
        if review_count >= 20:
            award_badge(user, 'Thánh Phê Bình', 'Sở hữu hơn 20 đánh giá chuyên sâu', 'fas fa-bullhorn', '#9b59b6')

# --- 3. HỆ THỐNG HUY HIỆU DANH SÁCH LƯU (Watchlist) ---
@receiver(post_save, sender=Watchlist)
def watchlist_achievements(sender, instance, created, **kwargs):
    if created:
        user = instance.user
        watch_count = Watchlist.objects.filter(user=user).count()

        # 5. Huy hiệu: Người Sưu Tầm (5 phim)
        if watch_count >= 5:
            award_badge(user, 'Người Sưu Tầm', 'Bắt đầu xây dựng kho phim cá nhân', 'fas fa-folder-plus', '#3498db')

        # 6. Huy hiệu: Tín Đồ Điện Ảnh (15 phim)
        if watch_count >= 15:
            award_badge(user, 'Tín Đồ Điện Ảnh', 'Sở hữu danh sách phim lưu trữ ấn tượng', 'fas fa-film', '#f1c40f')
            
        # 7. Huy hiệu: Kho Lưu Trữ Sống (50 phim)
        if watch_count >= 50:
            award_badge(user, 'Kho Lưu Trữ Sống', 'Lưu trữ hơn 50 bộ phim kinh điển', 'fas fa-database', '#e67e22')

# --- 4. HỆ THỐNG HUY HIỆU "ĐƯỢC YÊU THÍCH" (Dựa trên Like của Review) ---
# Logic này sẽ chạy mỗi khi một Review được cập nhật (ví dụ khi có người nhấn Like)
@receiver(post_save, sender=Review)
def social_achievements(sender, instance, **kwargs):
    user = instance.user
    # Đếm tổng số lượt like mà user nhận được từ tất cả các bài review của họ
    # Giả sử model Review của bạn có field 'likes' (ManyToMany)
    total_likes_received = sum(r.likes.count() for r in Review.objects.filter(user=user))

    # 8. Huy hiệu: Ý Kiến Hay (10 lượt like nhận được)
    if total_likes_received >= 10:
        award_badge(user, 'Ý Kiến Hay', 'Bình luận nhận được hơn 10 lượt yêu thích', 'fas fa-heart', '#ff4757')

    # 9. Huy hiệu: Người Truyền Cảm Hứng (50 lượt like nhận được)
    if total_likes_received >= 50:
        award_badge(user, 'Người Truyền Cảm Hứng', 'Những đánh giá có sức ảnh hưởng lớn', 'fas fa-fire', '#ff6b81')

# --- 5. HUY HIỆU ĐẶC BIỆT (Tạo thủ công hoặc qua sự kiện) ---
# 10. Huy hiệu: Nhà Tài Trợ (Tạo sẵn trong Admin và gán cho User ủng hộ)
# Bạn hãy vào Admin tạo Achievement tên "Nhà Tài Trợ", icon "fas fa-crown", màu "#ffcc00" 