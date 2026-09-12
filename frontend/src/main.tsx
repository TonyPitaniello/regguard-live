import { createRoot } from 'react-dom/client';

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
const RG_BUILD_ID = 'a2p-v1-20260911';

/**
 * Purge poisoned caches whenever BUILD_ID changes — not only once per epoch key.
 * Do NOT re-register a service worker while Arc is holding stale shells.
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

  if (previous) {
    const url = new URL(window.location.href);
    url.searchParams.set('v', RG_BUILD_ID);
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
    if (url.searchParams.has('rgbuild') || url.searchParams.has('forceclear')) {
      url.searchParams.delete('rgbuild');
      url.searchParams.delete('forceclear');
      window.history.replaceState({}, '', url.pathname + (url.search || '') + url.hash);
    }
  } catch {
    /* ignore */
  }

  // SW disabled (selfDestroying) until Arc cache poison is fully cleared.
  try {
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map((r) => r.unregister()));
    }
  } catch {
    /* ignore */
  }

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
