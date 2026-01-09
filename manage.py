#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.
File này là tiện ích dòng lệnh chính của Django dùng cho các tác vụ quản trị.
"""
import os
import sys


def main():
    """Run administrative tasks."""
    
    # Thiết lập biến môi trường để trỏ đến file cấu hình (settings.py) của dự án.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_project.settings')
    
    try:
        # Import hàm thực thi các lệnh từ dòng lệnh.
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Xử lý lỗi nếu Django chưa được cài đặt hoặc môi trường ảo chưa được kích hoạt.
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
        
    # Thực thi lệnh được truyền vào từ tham số dòng lệnh (ví dụ: runserver, migrate).
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    # Điểm khởi đầu của chương trình khi chạy file manage.py.
    main()