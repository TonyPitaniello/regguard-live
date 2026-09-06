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
  return /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

export function isStandaloneApp(): boolean {
  if (typeof window === 'undefined') return false;
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    nav.standalone === true
  );
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

export type LaunchAppMode =
  | 'standalone'
  | 'prompt'
  | 'ios'
  | 'manual';

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
    url.searchParams.set('repaired', '1');
    window.location.replace(url.pathname + url.search);
  }
}
