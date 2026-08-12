/**
 * Soft PWA install prompt — Chrome/Edge beforeinstallprompt.
 * iOS: show Add to Home Screen hint (no programmatic install).
 */
import { useEffect, useState } from 'react';
import { Download, X } from 'lucide-react';

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
};

function isIos(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

function isStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    nav.standalone === true
  );
}

export default function PwaInstallBanner() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [showIosHint, setShowIosHint] = useState(false);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    try {
      if (sessionStorage.getItem('pwaInstallDismissed') === '1') {
        setHidden(true);
        return;
      }
    } catch {
      /* ignore */
    }
    if (isStandalone()) {
      setHidden(true);
      return;
    }

    const onBip = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    window.addEventListener('beforeinstallprompt', onBip);

    if (isIos()) {
      setShowIosHint(true);
    }

    return () => window.removeEventListener('beforeinstallprompt', onBip);
  }, []);

  const dismiss = () => {
    setHidden(true);
    setDeferred(null);
    setShowIosHint(false);
    try {
      sessionStorage.setItem('pwaInstallDismissed', '1');
    } catch {
      /* ignore */
    }
  };

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    try {
      await deferred.userChoice;
    } catch {
      /* ignore */
    }
    setDeferred(null);
    dismiss();
  };

  if (hidden) return null;
  if (!deferred && !showIosHint) return null;

  return (
    <div
      className="fixed bottom-4 left-4 right-4 z-[90] mx-auto max-w-lg rounded-xl border border-emerald-500/40 bg-slate-950/95 p-3 shadow-lg backdrop-blur sm:left-auto"
      role="dialog"
      aria-label="Install Reg Guard"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-lg bg-emerald-500/15 p-2 text-emerald-300">
          <Download className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-white">Install Reg Guard</p>
          <p className="mt-0.5 text-xs text-gray-400">
            {deferred
              ? 'Add the standalone app for faster Bid Risk Receipts in bid week.'
              : 'On iPhone: Share → Add to Home Screen for a standalone app icon.'}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {deferred && (
              <button
                type="button"
                onClick={() => void install()}
                className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-500"
              >
                Install app
              </button>
            )}
            <button
              type="button"
              onClick={dismiss}
              className="rounded-lg border border-slate-600 px-3 py-2 text-xs font-semibold text-gray-300 hover:bg-slate-800"
            >
              Not now
            </button>
          </div>
        </div>
        <button
          type="button"
          onClick={dismiss}
          className="rounded-lg p-1 text-gray-500 hover:bg-slate-800 hover:text-white"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
