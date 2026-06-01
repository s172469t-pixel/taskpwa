const CACHE_NAME = 'taskpwa-v1';
const CACHED_URLS = ['/index.html', '/manifest.json'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(CACHED_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

self.addEventListener('sync', event => {
  if (event.tag === 'taskpwa-sync') {
    event.waitUntil(
      self.clients.matchAll({ type: 'window' }).then(list => {
        list.forEach(c => c.postMessage({ type: 'SYNC_TASKS' }));
      })
    );
  }
});

self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'タスク管理';
  const options = {
    body: data.body || '未完了タスクがあります',
    tag: 'taskpwa-push',
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const client of list) {
        if ('focus' in client) return client.focus();
      }
      return clients.openWindow('/index.html');
    })
  );
});
