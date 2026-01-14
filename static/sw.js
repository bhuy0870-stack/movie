const CACHE_NAME = 'bqh-movie-v2'; // Tăng lên v2 để cập nhật tính năng mới
const urlsToCache = [
  '/',
  '/static/images/icon-192.png',
  '/static/images/icon-512.png'
];

// 1. LẮNG NGHE SỰ KIỆN CÀI ĐẶT (INSTALL)
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// 2. LẮNG NGHE SỰ KIỆN FETCH (ĐỂ CHẠY OFFLINE)
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Trả về từ cache nếu có, không thì tải từ mạng
        return response || fetch(event.request);
      })
  );
});

// 3. LẮNG NGHE THÔNG BÁO PUSH TỪ SERVER
self.addEventListener('push', function(event) {
    let data = { title: 'BQH MOVIE', body: 'Có phim mới vừa cập nhật!', url: '/' };
    
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body,
        icon: '/static/images/icon-192.png',
        badge: '/static/images/icon-192.png',
        vibrate: [100, 50, 100],
        data: {
            url: data.url // Lưu link để khi click thì mở trang phim
        }
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// 4. XỬ LÝ KHI NGƯỜI DÙNG CLICK VÀO THÔNG BÁO
self.addEventListener('notificationclick', function(event) {
    event.notification.close(); // Đóng thông báo ngay lập tức

    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(windowClients => {
            // Kiểm tra xem trang web có đang mở sẵn không
            for (var i = 0; i < windowClients.length; i++) {
                var client = windowClients[i];
                if (client.url === event.notification.data.url && 'focus' in client) {
                    return client.focus();
                }
            }
            // Nếu chưa mở thì mở tab mới
            if (clients.openWindow) {
                return clients.openWindow(event.notification.data.url);
            }
        })
    );
});