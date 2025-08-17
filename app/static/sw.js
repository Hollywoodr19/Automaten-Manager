// Service Worker für Automaten Manager PWA
// Version 1.0.0

const CACHE_NAME = 'automaten-manager-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/login',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css'
];

// Dynamische Routen die gecacht werden sollen
const dynamicRoutes = [
  '/dashboard',
  '/devices',
  '/income',
  '/expenses',
  '/products',
  '/suppliers',
  '/reports',
  '/settings'
];

// Install Event - Cache erstellen
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache opened');
        return cache.addAll(urlsToCache);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate Event - Alte Caches löschen
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event - Network First Strategy für API, Cache First für Assets
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // API Calls - Network First
  if (url.pathname.startsWith('/api/') || request.method !== 'GET') {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Clone response für Cache
          if (response.status === 200) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(request, responseToCache);
              });
          }
          return response;
        })
        .catch(() => {
          // Fallback auf Cache bei Offline
          return caches.match(request);
        })
    );
    return;
  }
  
  // Static Assets - Cache First
  event.respondWith(
    caches.match(request)
      .then(response => {
        if (response) {
          return response;
        }
        
        return fetch(request).then(response => {
          // 404er nicht cachen
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }
          
          const responseToCache = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(request, responseToCache);
            });
          
          return response;
        });
      })
      .catch(() => {
        // Offline Fallback Page
        if (request.mode === 'navigate') {
          return caches.match('/offline.html');
        }
      })
  );
});

// Background Sync für Offline-Eingaben
self.addEventListener('sync', event => {
  if (event.tag === 'sync-entries') {
    event.waitUntil(syncEntries());
  }
});

async function syncEntries() {
  const db = await openDB();
  const tx = db.transaction('pendingEntries', 'readonly');
  const store = tx.objectStore('pendingEntries');
  const entries = await store.getAll();
  
  for (const entry of entries) {
    try {
      const response = await fetch('/api/entries', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(entry)
      });
      
      if (response.ok) {
        // Eintrag aus IndexedDB löschen
        const deleteTx = db.transaction('pendingEntries', 'readwrite');
        await deleteTx.objectStore('pendingEntries').delete(entry.id);
      }
    } catch (error) {
      console.error('Sync failed for entry:', entry, error);
    }
  }
}

// Push Notifications
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : 'Neue Benachrichtigung',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Öffnen',
        icon: '/static/icons/checkmark.png'
      },
      {
        action: 'close',
        title: 'Schließen',
        icon: '/static/icons/xmark.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Automaten Manager', options)
  );
});

// Notification Click Handler
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  if (event.action === 'explore') {
    // Öffne App
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// IndexedDB Helper für Offline Storage
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('AutomatenManagerDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = event => {
      const db = event.target.result;
      
      if (!db.objectStoreNames.contains('pendingEntries')) {
        db.createObjectStore('pendingEntries', { keyPath: 'id', autoIncrement: true });
      }
      
      if (!db.objectStoreNames.contains('cachedData')) {
        const store = db.createObjectStore('cachedData', { keyPath: 'key' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

// Periodische Hintergrund-Synchronisation
self.addEventListener('periodicsync', event => {
  if (event.tag === 'update-data') {
    event.waitUntil(updateData());
  }
});

async function updateData() {
  try {
    // Dashboard-Daten aktualisieren
    const response = await fetch('/api/dashboard/stats');
    if (response.ok) {
      const data = await response.json();
      
      // In IndexedDB speichern
      const db = await openDB();
      const tx = db.transaction('cachedData', 'readwrite');
      await tx.objectStore('cachedData').put({
        key: 'dashboard_stats',
        data: data,
        timestamp: Date.now()
      });
    }
  } catch (error) {
    console.error('Background update failed:', error);
  }
}

// Message Handler für Client-Kommunikation
self.addEventListener('message', event => {
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(CACHE_NAME)
        .then(cache => cache.addAll(event.data.urls))
    );
  }
});

console.log('Service Worker loaded - Version 1.0.0');
