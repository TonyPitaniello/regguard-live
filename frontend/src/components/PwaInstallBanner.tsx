/**
 * Soft PWA install prompt — Chrome/Edge beforeinstallprompt.
 * iOS: show Add to Home Screen hint (no programmatic install).
 */
import { useEffect, useState } from 'react';
import { Download, X } from 'lucide-react';
import {
  ensurePwaInstallListener,
  getDeferredInstallPrompt,
  getLaunchAppMode,
  isStandaloneApp,
  promptPwaInstall,
  subscribePwaInstall,
} from '../pwaInstall';

export default function PwaInstallBanner() {
  const [canPrompt, setCanPrompt] = useState(false);
  const [mode, setMode] = useState(() => getLaunchAppMode());
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    ensurePwaInstallListener();
    try {
      if (sessionStorage.getItem('pwaInstallDismissed') === '1') {
        setHidden(true);
        return;
      }
    } catch {
      /* ignore */
    }
    if (isStandaloneApp()) {
      setHidden(true);
      return;
    }

    const sync = () => {
      setCanPrompt(Boolean(getDeferredInstallPrompt()));
      setMode(getLaunchAppMode());
    };
    sync();
    return subscribePwaInstall(sync);
  }, []);

  const dismiss = () => {
    setHidden(true);
    try {
      sessionStorage.setItem('pwaInstallDismissed', '1');
    } catch {
      /* ignore */
    }
  };

  const install = async () => {
    const outcome = await promptPwaInstall();
    if (outcome === 'accepted') dismiss();
  };

  if (hidden) return null;
  if (mode === 'standalone') return null;
  if (!canPrompt && mode !== 'ios') return null;

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
          <p className="text-sm font-bold text-white">Launch Reg Guard as an app</p>
          <p className="mt-0.5 text-xs text-gray-400">
            {canPrompt
              ? 'Install for one-tap Bid Risk Receipts — works offline for recent pages.'
              : 'On iPhone: tap Share → Add to Home Screen. Then open Reg Guard from your home screen.'}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {canPrompt && (
              <button
                type="button"
                onClick={() => void install()}
                className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-500 min-h-[44px]"
              >
                Launch app
              </button>
            )}
            <button
              type="button"
              onClick={dismiss}
              className="rounded-lg border border-slate-600 px-3 py-2 text-xs font-semibold text-gray-300 hover:bg-slate-800 min-h-[44px]"
            >
              Not now
            </button>
          </div>
        </div>
        <button
          type="button"
          onClick={dismiss}
          className="rounded-lg p-1 text-gray-500 hover:bg-slate-800 hover:text-white min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
