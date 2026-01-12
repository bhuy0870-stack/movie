# main/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Giao diện chính
    path('', views.home, name='home'), 
    
    # Chi tiết phim - Chỉ dùng 1 dòng duy nhất cho Slug
    path('movie/<slug:slug>/', views.movie_detail, name='movie_detail'),
    
    # Watchlist
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('toggle-watchlist/<int:movie_id>/', views.toggle_watchlist, name='toggle_watchlist'),

    # Xác thực người dùng
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),  
    path('profile/update-avatar/', views.update_avatar, name='update_avatar'),

    # Tương tác & Tìm kiếm
    path('ajax-search/', views.ajax_search, name='ajax_search'),
    path('movie/<int:movie_id>/review/add/', views.add_review, name='add_review'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),
    path('like-review/<int:review_id>/', views.like_review, name='like_review'), 

    path('update-history/<int:movie_id>/', views.update_history, name='update_history'),
    path('history/', views.history_view, name='history'),
    path('history/delete/<int:history_id>/', views.delete_history, name='delete_history'),
    path('history/', views.history_view, name='history'),
]