const CACHE_NAME = 'phoenixgcode-web-v1';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './css/main.css',
  './js/app.js',
  './js/console.js',
  './js/inspector.js',
  './js/python-bridge.js',
  './manifest.json',
  './assets/icon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      return cachedResponse || fetch(event.request);
    })
  );
});