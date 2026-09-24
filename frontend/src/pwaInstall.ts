/**
 * Shared PWA install prompt capture — menu + banner share one deferred event.
 */

export type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
};

type Listener = () => void;

let deferred: BeforeInstallPromptEvent | null = null;
let listening = false;
const listeners = new Set<Listener>();

const BOOT_RECOVERY_KEY = 'rg_sw_recovery';
const BOOT_OK_KEY = 'rg_boot_ok';

const APP_ORIGIN = 'https://app.regguardagent.com';
const SHARE_TITLE = 'Reg Guard';
const SHARE_TEXT =
  'Citeable site diligence before you bid — forwardable Bid Risk Receipt.';

function notify() {
  listeners.forEach((fn) => {
    try {
      fn();
    } catch {
      /* ignore */
    }
  });
}

export function isIosDevice(): boolean {
  if (typeof navigator === 'undefined') return false;
  return (
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  );
}

/**
 * True only when running as an installed home-screen / PWA window.
 * On iOS, ONLY trust navigator.standalone — matchMedia('standalone') can
 * falsely flip true in Safari tabs after load and hide Launch/Get app.
 */
export function isStandaloneApp(): boolean {
  if (typeof window === 'undefined') return false;
  const nav = window.navigator as Navigator & { standalone?: boolean };
  if (isIosDevice()) {
    return nav.standalone === true;
  }
  try {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      window.matchMedia('(display-mode: fullscreen)').matches
    );
  } catch {
    return false;
  }
}

/** Coarse phone/tablet signal for always showing install entry points. */
export function isMobileViewport(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return window.matchMedia('(max-width: 768px)').matches || navigator.maxTouchPoints > 1;
  } catch {
    return navigator.maxTouchPoints > 1;
  }
}

export function ensurePwaInstallListener(): void {
  if (typeof window === 'undefined' || listening) return;
  listening = true;
  window.addEventListener('beforeinstallprompt', (e: Event) => {
    e.preventDefault();
    deferred = e as BeforeInstallPromptEvent;
    notify();
  });
  window.addEventListener('appinstalled', () => {
    deferred = null;
    notify();
  });
}

export function getDeferredInstallPrompt(): BeforeInstallPromptEvent | null {
  return deferred;
}

export function subscribePwaInstall(listener: Listener): () => void {
  ensurePwaInstallListener();
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export async function promptPwaInstall(): Promise<'accepted' | 'dismissed' | 'unavailable'> {
  ensurePwaInstallListener();
  const event = deferred;
  if (!event) return 'unavailable';
  try {
    await event.prompt();
    const choice = await event.userChoice;
    deferred = null;
    notify();
    return choice.outcome;
  } catch {
    deferred = null;
    notify();
    return 'dismissed';
  }
}

export type OneClickInstallResult =
  | 'accepted'
  | 'dismissed'
  | 'ios_share'
  | 'already_installed'
  | 'unavailable';

function waitForDeferredPrompt(ms: number): Promise<BeforeInstallPromptEvent | null> {
  if (deferred) return Promise.resolve(deferred);
  return new Promise((resolve) => {
    const start = Date.now();
    const tick = () => {
      if (deferred) {
        resolve(deferred);
        return;
      }
      if (Date.now() - start >= ms) {
        resolve(null);
        return;
      }
      window.setTimeout(tick, 100);
    };
    tick();
  });
}

/** Make sure the SW is active + controlling — required for Chromium install prompt. */
async function ensureServiceWorkerControlling(ms = 2500): Promise<void> {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    if (reg.waiting) {
      try {
        reg.waiting.postMessage({ type: 'SKIP_WAITING' });
      } catch {
        /* ignore */
      }
    }
    if (navigator.serviceWorker.controller) return;
    await new Promise<void>((resolve) => {
      const done = () => resolve();
      const t = window.setTimeout(done, ms);
      navigator.serviceWorker.addEventListener(
        'controllerchange',
        () => {
          window.clearTimeout(t);
          done();
        },
        { once: true }
      );
    });
  } catch {
    /* ignore */
  }
}

function appShareUrl(): string {
  try {
    if (typeof window !== 'undefined' && window.location?.origin) {
      return `${window.location.origin}/`;
    }
  } catch {
    /* ignore */
  }
  return `${APP_ORIGIN}/`;
}

/** Share sheet — must stay on the user-gesture call stack (no instruction UI). */
async function shareInstall(): Promise<'ios_share' | 'unavailable'> {
  if (typeof navigator === 'undefined' || typeof navigator.share !== 'function') {
    return 'unavailable';
  }
  try {
    await navigator.share({
      title: SHARE_TITLE,
      text: SHARE_TEXT,
      url: appShareUrl(),
    });
    return 'ios_share';
  } catch (err) {
    if (err && typeof err === 'object' && 'name' in err && (err as { name: string }).name === 'AbortError') {
      return 'ios_share';
    }
    return 'unavailable';
  }
}

/**
 * One push of Download: Chromium install dialog, or Share sheet.
 * Never opens instruction pages / secondary buttons.
 */
export async function oneClickInstallApp(): Promise<OneClickInstallResult> {
  ensurePwaInstallListener();
  if (isStandaloneApp()) return 'already_installed';

  // iOS first — preserve the click gesture for navigator.share
  if (isIosDevice()) {
    return shareInstall();
  }

  // Chromium: SW must control the page before beforeinstallprompt is reliable
  await ensureServiceWorkerControlling(2000);
  if (!deferred) {
    await waitForDeferredPrompt(3500);
  }
  const native = await promptPwaInstall();
  if (native === 'accepted') return 'accepted';
  if (native === 'dismissed') return 'dismissed';

  // Desktop Safari / browsers without beforeinstallprompt — still one gesture
  return shareInstall();
}

export type LaunchAppMode = 'standalone' | 'prompt' | 'ios' | 'manual';

export function getLaunchAppMode(): LaunchAppMode {
  if (isStandaloneApp()) return 'standalone';
  if (getDeferredInstallPrompt()) return 'prompt';
  if (isIosDevice()) return 'ios';
  return 'manual';
}

/** Mark that React successfully mounted (cancels blank-screen SW recovery). */
export function markAppBootOk(): void {
  try {
    sessionStorage.setItem(BOOT_OK_KEY, '1');
    sessionStorage.removeItem(BOOT_RECOVERY_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Unregister service workers + clear Cache Storage, then hard-reload.
 * Fixes home-screen / Launch app blanks after a bad deploy cache.
 */
export async function repairPwaInstall(reload = true): Promise<void> {
  deferred = null;
  notify();
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
  try {
    sessionStorage.removeItem(BOOT_OK_KEY);
    sessionStorage.setItem(BOOT_RECOVERY_KEY, '1');
  } catch {
    /* ignore */
  }
  if (reload && typeof window !== 'undefined') {
    try {
      localStorage.removeItem('rg_pwa_epoch_3');
    } catch {
      /* ignore */
    }
    const url = new URL(window.location.href);
    window.location.replace(url.pathname || '/');
  }
}
