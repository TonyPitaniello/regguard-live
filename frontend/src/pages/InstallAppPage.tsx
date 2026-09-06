/**
 * Dedicated install page — guaranteed navigation target when "Launch app"
 * must not depend on a modal or a hanging serviceWorker.ready promise.
 */
import { useEffect, useState } from 'react';
import { Download, Smartphone } from 'lucide-react';
import {
  getDeferredInstallPrompt,
  getLaunchAppMode,
  isIosDevice,
  isStandaloneApp,
  promptPwaInstall,
  repairPwaInstall,
  subscribePwaInstall,
} from '../pwaInstall';

export default function InstallAppPage() {
  const [mode, setMode] = useState(() => getLaunchAppMode());
  const [canPrompt, setCanPrompt] = useState(false);
  const [status, setStatus] = useState('');

  useEffect(() => {
    const sync = () => {
      setCanPrompt(Boolean(getDeferredInstallPrompt()));
      setMode(getLaunchAppMode());
    };
    sync();
    return subscribePwaInstall(sync);
  }, []);

  useEffect(() => {
    if (isStandaloneApp()) {
      setStatus('Reg Guard is already running as an app on this device.');
    }
  }, []);

  const tryNativeInstall = async () => {
    setStatus('Checking install…');
    const outcome = await promptPwaInstall();
    if (outcome === 'accepted') {
      setStatus('Installed. Open Reg Guard from your home screen.');
      return;
    }
    if (outcome === 'dismissed') {
      setStatus('Install was dismissed. You can still add it from the browser menu.');
      return;
    }
    setStatus(
      isIosDevice()
        ? 'On iPhone, use Share → Add to Home Screen (below).'
        : 'Use your browser menu → Install app / Add to Home screen.'
    );
  };

  return (
    <div className="mx-auto max-w-lg px-4 py-8 text-slate-200">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-emerald-500/15 p-3 text-emerald-300">
          {isStandaloneApp() ? <Smartphone className="h-7 w-7" /> : <Download className="h-7 w-7" />}
        </div>
        <div>
          <h1 className="text-2xl font-black text-white">Launch Reg Guard as an app</h1>
          <p className="text-sm text-slate-400">One-tap from your home screen</p>
        </div>
      </div>

      {status ? (
        <p className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
          {status}
        </p>
      ) : null}

      {(canPrompt || mode === 'prompt') && (
        <button
          type="button"
          onClick={() => void tryNativeInstall()}
          className="mb-4 w-full min-h-[52px] rounded-xl bg-emerald-600 px-4 py-3 text-base font-bold text-white hover:bg-emerald-500"
        >
          Install Reg Guard now
        </button>
      )}

      {isIosDevice() || mode === 'ios' ? (
        <ol className="mb-6 list-decimal space-y-3 pl-5 text-[15px] leading-relaxed text-slate-300">
          <li>
            Stay in <strong className="text-emerald-300">Safari</strong> (or Chrome on iOS 16.4+).
          </li>
          <li>
            Tap the <strong className="text-emerald-300">Share</strong> button (square with arrow).
          </li>
          <li>
            Scroll and tap <strong className="text-emerald-300">Add to Home Screen</strong>, then{' '}
            <strong className="text-emerald-300">Add</strong>.
          </li>
          <li>
            Open <strong className="text-emerald-300">Reg Guard</strong> from your home screen — not
            from a Safari tab.
          </li>
        </ol>
      ) : (
        <ol className="mb-6 list-decimal space-y-3 pl-5 text-[15px] leading-relaxed text-slate-300">
          <li>
            Open the browser menu (<strong className="text-emerald-300">⋮</strong> or{' '}
            <strong className="text-emerald-300">⋯</strong>).
          </li>
          <li>
            Tap <strong className="text-emerald-300">Install app</strong> or{' '}
            <strong className="text-emerald-300">Add to Home screen</strong>.
          </li>
          <li>
            Open <strong className="text-emerald-300">Reg Guard</strong> from your home screen.
          </li>
        </ol>
      )}

      <button
        type="button"
        onClick={() => void repairPwaInstall(true)}
        className="w-full min-h-[48px] rounded-xl border border-slate-600 px-4 py-3 text-sm font-semibold text-slate-200 hover:bg-slate-800"
      >
        Repair app (clear cache &amp; reload)
      </button>
      <p className="mt-3 text-xs text-slate-500">
        Use Repair if the home-screen icon opens a blank screen after an update.
      </p>
    </div>
  );
}
