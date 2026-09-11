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

/** Bump on every user-facing UI ship that must defeat stale SW / Arc / PWA caches. */
const RG_BUILD_ID = 'exec-v4-20260910';

/**
 * Purge poisoned caches whenever BUILD_ID changes — not only once per epoch key.
 */
async function migrateStalePwaCaches(): Promise<boolean> {
  let previous = '';
  try {
    previous = localStorage.getItem('rg_build_id') || '';
  } catch {
    previous = '';
  }

  if (previous === RG_BUILD_ID) return false;

  try {
    localStorage.setItem('rg_build_id', RG_BUILD_ID);
  } catch {
    /* ignore */
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

  // Always reload once after a build-id change so HTML+JS cannot stay half-stale.
  if (previous || hadController) {
    const url = new URL(window.location.href);
    url.searchParams.set('rgbuild', RG_BUILD_ID);
    window.location.replace(url.toString());
    return true;
  }
  return false;
}

async function boot() {
  // Capture install prompt as early as possible (before React mounts)
  ensurePwaInstallListener();

  const reloading = await migrateStalePwaCaches();
  if (reloading) return;

  // Strip one-time cache-bust query after successful boot
  try {
    const url = new URL(window.location.href);
    if (url.searchParams.has('rgbuild')) {
      url.searchParams.delete('rgbuild');
      window.history.replaceState({}, '', url.pathname + (url.search || '') + url.hash);
    }
  } catch {
    /* ignore */
  }

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
