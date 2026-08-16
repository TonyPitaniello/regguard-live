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
