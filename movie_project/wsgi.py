"""
WSGI config for movie_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# =========================================================================
# KHỐI CẤU HÌNH WSGI
# =========================================================================

# Thiết lập biến môi trường trỏ đến file settings của dự án.
# Điều này cho Django biết nên sử dụng cấu hình nào.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_project.settings')

# Khởi tạo ứng dụng WSGI. 
# Hàm này tạo ra một callable (đối tượng có thể gọi) được máy chủ WSGI sử dụng.
application = get_wsgi_application()