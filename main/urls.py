# main/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Giao diện chính
    path('', views.home, name='home'), 
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('watchlist/toggle/<int:movie_id>/', views.toggle_watchlist, name='toggle_watchlist'),
    # Xác thực người dùng
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),  
    path('like-review/<int:review_id>/', views.like_review, name='like_review'), 
    # Xử lý Review/Bình luận
    path('movie/<int:movie_id>/review/add/', views.add_review, name='add_review'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),
    
]