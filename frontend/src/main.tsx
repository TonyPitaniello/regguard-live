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
const RG_BUILD_ID = 'launch-20260924-clean-url';

/** Internal params that must never linger in the address bar. */
const VANITY_QUERY_KEYS = ['v', 'forceclear', 'rgbuild', 'source', 'repaired'] as const;

function cleanAddressBar(): void {
  try {
    const url = new URL(window.location.href);
    let changed = false;
    for (const key of VANITY_QUERY_KEYS) {
      if (url.searchParams.has(key)) {
        url.searchParams.delete(key);
        changed = true;
      }
    }
    if (!changed) return;
    const q = url.searchParams.toString();
    window.history.replaceState({}, '', url.pathname + (q ? `?${q}` : '') + url.hash);
  } catch {
    /* ignore */
  }
}

/**
 * Soft cache refresh on BUILD_ID change — do NOT unregister the service worker.
 * Do NOT put ?v= in the address bar. One session-guarded reload is enough.
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
    if ('caches' in window) {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }
  } catch {
    /* ignore */
  }

  if (previous) {
    const reloadKey = `rg_bust_reload_${RG_BUILD_ID}`;
    try {
      if (!sessionStorage.getItem(reloadKey)) {
        sessionStorage.setItem(reloadKey, '1');
        window.location.reload();
        return true;
      }
      sessionStorage.removeItem(reloadKey);
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
          // Activate waiting worker ASAP so Chromium can offer install on this visit.
          if (registration?.waiting) {
            registration.waiting.postMessage({ type: 'SKIP_WAITING' });
          }
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
  cleanAddressBar();

  // Belt-and-suspenders with index.html: F5 / Cmd+R on any deep page → home
  if (redirectHardRefreshToHome()) return;

  const reloading = await migrateStalePwaCaches();
  if (reloading) {
    // Safety net: if reload was a silent no-op, still mount after a tick.
    window.setTimeout(() => {
      if (document.getElementById('root')?.childElementCount) return;
      void mountApp();
    }, 400);
    return;
  }

  await mountApp();
}

async function mountApp() {
  cleanAddressBar();

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
