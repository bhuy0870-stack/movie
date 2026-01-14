const CACHE_NAME = 'bqh-movie-v1';
const urlsToCache = [
  '/',
  '/static/images/icon-192.png',
  '/static/images/icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        // Sử dụng return để đảm bảo cache xong mới kết thúc install
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        return response || fetch(event.request);
      })
  );
});