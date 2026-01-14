const CACHE_NAME = 'bqh-movie-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css', // Nếu bạn có file css riêng
  '/static/images/icon-192.png',
  '/static/images/icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
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