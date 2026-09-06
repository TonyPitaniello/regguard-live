import { createRoot } from 'react-dom/client';
import { registerSW } from 'virtual:pwa-register';

import { AppRouter } from './AppRouter';
import { ErrorBoundary } from './components/ErrorBoundary';
import { loadGoogleMapsApi } from './loadGoogleMaps';
import { ensurePwaInstallListener, markAppBootOk } from './pwaInstall';

import './index.css'; // Tailwind CSS + base styles
import 'react-toastify/dist/ReactToastify.css';
import './voice-command.css';
import './onboarding-system.css';
import './mobile-optimizations.css'; // Mobile performance optimization

const PWA_EPOCH = 'rg_pwa_epoch_3';

/**
 * One-time purge of poisoned precaches from older deploys.
 * Home-screen icons often opened a blank shell because SW served stale index+chunk hashes.
 */
async function migrateStalePwaCaches(): Promise<boolean> {
  try {
    if (localStorage.getItem(PWA_EPOCH) === '1') return false;
    localStorage.setItem(PWA_EPOCH, '1');
  } catch {
    return false;
  }

  let hadController = false;
  try {
    hadController = Boolean(navigator.serviceWorker?.controller);
  } catch {
    hadController = false;
  }

  try {
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map((r) => r.unregister()));
    }
  } catch {
    /* ignore */
  }

  try {
    if ('caches' in window) {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }
  } catch {
    /* ignore */
  }

  if (hadController) {
    window.location.reload();
    return true;
  }
  return false;
}

async function boot() {
  // Capture install prompt as early as possible (before React mounts)
  ensurePwaInstallListener();

  const reloading = await migrateStalePwaCaches();
  if (reloading) return;

  // Network-first SW — keeps Android installability without blank shells.
  registerSW({
    immediate: true,
    onRegisteredSW(_swUrl, registration) {
      if (!registration) return;
      window.setInterval(() => {
        void registration.update();
      }, 60 * 60 * 1000);
    },
  });

  createRoot(document.getElementById('root')!).render(
    <ErrorBoundary>
      <AppRouter />
    </ErrorBoundary>
  );

  // Mark boot only after first paint so blank-shell recovery can still fire.
  window.requestAnimationFrame(() => {
    window.setTimeout(() => markAppBootOk(), 50);
  });

  loadGoogleMapsApi().catch((err) =>
    console.warn('Google Maps failed (non-blocking):', err)
  );
}

void boot();
