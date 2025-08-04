const CACHE_NAME = 'ol-quickstatements-v1';
const urlsToCache = [
    '/',
    'index.html',
    'https://unpkg.com/vue@3/dist/vue.global.js',
    'https://cdn.tailwindcss.com',
    'https://cdn.jsdelivr.net/npm/jq-web@0.6.0/jq.min.js',
    'https://cdn.jsdelivr.net/npm/deep-diff@1/dist/deep-diff.min.js',
    'https://cdn.jsdelivr.net/npm/notyf@3/notyf.min.css',
    'https://cdn.jsdelivr.net/npm/notyf@3/notyf.min.js'
];

// Install event - cache all required assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});

// Call fetch event
self.addEventListener('fetch', (e) => {
    console.log('Service Worker: Fetching');
    e.respondWith(
        caches.match(e.request).then(response => {
            return response || fetch(e.request);
        })
    );
});

// Call activate event
self.addEventListener('activate', (e) => {
    console.log('Service Worker: Activated');
    // Remove unwanted caches
    e.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    if (cache !== CACHE_NAME) {
                        console.log('Service Worker: Clearing Old Cache');
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
});
