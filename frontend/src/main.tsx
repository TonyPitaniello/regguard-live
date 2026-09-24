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
const RG_BUILD_ID = 'launch-20260924-download-onepush';

/**
 * Purge poisoned caches whenever BUILD_ID changes — not only once per epoch key.
 * Critical: never return without mounting if replace would be a same-URL no-op
 * (Arc/Chromium skip navigation → permanent blank #root).
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

  // Only hard-navigate when the bust query actually changes the URL.
  if (previous) {
    try {
      const url = new URL(window.location.href);
      if (url.searchParams.get('v') === RG_BUILD_ID) {
        return false;
      }
      url.searchParams.set('v', RG_BUILD_ID);
      window.location.replace(url.toString());
      return true;
    } catch {
      return false;
    }
  }
  return false;
}

function redirectHardRefreshToHome(): boolean {
  try {
    const nav = performance.getEntriesByType?.(
      'navigation'
    )?.[0] as PerformanceNavigationTiming | undefined;
    if (!nav || nav.type !== 'reload') return false;
    const path = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
    if (path === '/' || path === '/index.html') return false;
    window.location.replace('/');
    return true;
  } catch {
    return false;
  }
}

function registerInstallableServiceWorker(): void {
  try {
    // NetworkOnly navigations in workbox + autoUpdate keep installability without
    // serving stale JS shells. Required for Chrome/Edge beforeinstallprompt.
    registerSW({
      immediate: true,
      onRegisteredSW(_url, registration) {
        try {
          void registration?.update();
        } catch {
          /* ignore */
        }
      },
    });
  } catch (err) {
    console.warn('[Reg Guard] PWA register failed (install still available via browser menu)', err);
  }
}

async function boot() {
  // Capture install prompt as early as possible (before React mounts)
  ensurePwaInstallListener();

  // Belt-and-suspenders with index.html: F5 / Cmd+R on any deep page → home
  if (redirectHardRefreshToHome()) return;

  const reloading = await migrateStalePwaCaches();
  if (reloading) {
    // Safety net: if replace was a silent no-op, still mount after a tick.
    window.setTimeout(() => {
      if (document.getElementById('root')?.childElementCount) return;
      void mountApp();
    }, 400);
    return;
  }

  await mountApp();
}

async function mountApp() {
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

  registerInstallableServiceWorker();

  const rootEl = document.getElementById('root');
  if (!rootEl) return;
  if (rootEl.childElementCount > 0) return;

  createRoot(rootEl).render(
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
