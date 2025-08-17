// PWA Initialization Script
// Wird in die base.html eingebunden

let deferredPrompt;
let isAppInstalled = false;

// Service Worker registrieren
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('ServiceWorker registered:', registration);
                
                // Update Check
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            // Neue Version verfügbar
                            showUpdateNotification();
                        }
                    });
                });
            })
            .catch(err => {
                console.log('ServiceWorker registration failed:', err);
            });
    });
}

// Install Prompt Handler
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    // Install-Button anzeigen
    showInstallButton();
});

// App Installed Handler
window.addEventListener('appinstalled', () => {
    console.log('PWA was installed');
    isAppInstalled = true;
    hideInstallButton();
    
    // Analytics Event
    if (typeof gtag !== 'undefined') {
        gtag('event', 'app_installed');
    }
});

// Install Button anzeigen
function showInstallButton() {
    const installContainer = document.getElementById('pwa-install-container');
    if (installContainer) {
        installContainer.style.display = 'block';
    }
    
    // Banner nach 5 Sekunden zeigen
    setTimeout(() => {
        showInstallBanner();
    }, 5000);
}

// Install Banner
function showInstallBanner() {
    if (isAppInstalled || !deferredPrompt) return;
    
    const banner = document.createElement('div');
    banner.className = 'pwa-install-banner';
    banner.innerHTML = `
        <div class="pwa-banner-content">
            <div class="pwa-banner-icon">
                <i class="bi bi-phone"></i>
            </div>
            <div class="pwa-banner-text">
                <strong>App installieren</strong>
                <small>Für schnelleren Zugriff auf Ihrem Gerät</small>
            </div>
            <div class="pwa-banner-actions">
                <button onclick="installPWA()" class="btn btn-sm btn-primary">Installieren</button>
                <button onclick="dismissInstallBanner()" class="btn btn-sm btn-light">Später</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(banner);
    
    // Auto-dismiss nach 10 Sekunden
    setTimeout(() => {
        dismissInstallBanner();
    }, 10000);
}

// PWA installieren
async function installPWA() {
    if (!deferredPrompt) return;
    
    // Prompt anzeigen
    deferredPrompt.prompt();
    
    // Warten auf User-Entscheidung
    const { outcome } = await deferredPrompt.userChoice;
    
    console.log(`User response: ${outcome}`);
    
    // Analytics
    if (typeof gtag !== 'undefined') {
        gtag('event', 'install_prompt_response', {
            'response': outcome
        });
    }
    
    // Reset
    deferredPrompt = null;
    dismissInstallBanner();
}

// Banner schließen
function dismissInstallBanner() {
    const banner = document.querySelector('.pwa-install-banner');
    if (banner) {
        banner.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            banner.remove();
        }, 300);
    }
}

// Install Button verstecken
function hideInstallButton() {
    const installContainer = document.getElementById('pwa-install-container');
    if (installContainer) {
        installContainer.style.display = 'none';
    }
}

// Update Notification
function showUpdateNotification() {
    const notification = document.createElement('div');
    notification.className = 'pwa-update-notification';
    notification.innerHTML = `
        <div class="alert alert-info m-3">
            <i class="bi bi-arrow-clockwise"></i>
            <strong>Update verfügbar!</strong>
            Eine neue Version der App ist verfügbar.
            <button onclick="updateApp()" class="btn btn-sm btn-primary ms-2">Aktualisieren</button>
        </div>
    `;
    
    const container = document.querySelector('.main-content') || document.body;
    container.insertBefore(notification, container.firstChild);
}

// App updaten
function updateApp() {
    if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
        window.location.reload();
    }
}

// Online/Offline Status
window.addEventListener('online', () => {
    showOnlineNotification();
    syncPendingData();
});

window.addEventListener('offline', () => {
    showOfflineNotification();
});

// Online Notification
function showOnlineNotification() {
    showToast('Verbindung wiederhergestellt', 'success');
}

// Offline Notification
function showOfflineNotification() {
    showToast('Offline-Modus - Daten werden lokal gespeichert', 'warning');
}

// Toast Notification Helper
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Offline Data Sync
async function syncPendingData() {
    if ('sync' in self.registration) {
        try {
            await self.registration.sync.register('sync-entries');
            console.log('Background sync registered');
        } catch (err) {
            console.log('Background sync failed:', err);
        }
    }
}

// Push Notifications aktivieren
async function enablePushNotifications() {
    if (!('Notification' in window)) {
        console.log('Notifications not supported');
        return;
    }
    
    if (Notification.permission === 'granted') {
        subscribeToPush();
    } else if (Notification.permission !== 'denied') {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
            subscribeToPush();
        }
    }
}

// Push Subscription
async function subscribeToPush() {
    try {
        const registration = await navigator.serviceWorker.ready;
        
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY)
        });
        
        // Subscription an Server senden
        await fetch('/api/push/subscribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(subscription)
        });
        
        console.log('Push subscription successful');
    } catch (error) {
        console.error('Push subscription failed:', error);
    }
}

// Helper für VAPID Key
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// PWA Styles
const pwaStyles = `
<style>
.pwa-install-banner {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    padding: 15px 20px;
    z-index: 10000;
    animation: slideUp 0.3s ease-out;
    max-width: 90%;
    width: 400px;
}

.pwa-banner-content {
    display: flex;
    align-items: center;
    gap: 15px;
}

.pwa-banner-icon {
    font-size: 32px;
    color: #667eea;
}

.pwa-banner-text {
    flex: 1;
}

.pwa-banner-text strong {
    display: block;
    margin-bottom: 2px;
}

.pwa-banner-text small {
    color: #666;
    font-size: 12px;
}

.pwa-banner-actions {
    display: flex;
    gap: 8px;
}

@keyframes slideUp {
    from {
        transform: translate(-50%, 100px);
        opacity: 0;
    }
    to {
        transform: translate(-50%, 0);
        opacity: 1;
    }
}

@keyframes slideOut {
    from {
        transform: translate(-50%, 0);
        opacity: 1;
    }
    to {
        transform: translate(-50%, 100px);
        opacity: 0;
    }
}

@keyframes fadeOut {
    from { opacity: 1; }
    to { opacity: 0; }
}

.toast-notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: white;
    padding: 12px 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    z-index: 10001;
    animation: slideInRight 0.3s ease-out;
}

.toast-content {
    display: flex;
    align-items: center;
    gap: 10px;
}

.toast-success { border-left: 4px solid #28a745; }
.toast-warning { border-left: 4px solid #ffc107; }
.toast-info { border-left: 4px solid #17a2b8; }

@keyframes slideInRight {
    from {
        transform: translateX(100px);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* iOS PWA Optimierungen */
@media (display-mode: standalone) {
    .pwa-install-banner {
        display: none !important;
    }
    
    /* iOS Status Bar */
    body {
        padding-top: env(safe-area-inset-top);
    }
}

/* Offline Indicator */
.offline-indicator {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: #ffc107;
    color: black;
    text-align: center;
    padding: 8px;
    z-index: 9999;
    font-size: 14px;
}
</style>
`;

// Styles injizieren
document.head.insertAdjacentHTML('beforeend', pwaStyles);

// VAPID Public Key (muss noch generiert werden)
const PUBLIC_VAPID_KEY = 'YOUR_PUBLIC_VAPID_KEY_HERE';

console.log('PWA Script loaded');
