/**
 * Install page — on iPhone this is an instant Share → Add to Home Screen flow.
 */
import { useEffect, useState } from 'react';
import { Download, Smartphone, Share, PlusSquare } from 'lucide-react';
import {
  getDeferredInstallPrompt,
  getLaunchAppMode,
  isIosDevice,
  isStandaloneApp,
  promptPwaInstall,
  repairPwaInstall,
  subscribePwaInstall,
} from '../pwaInstall';
import IosInstantInstall, { openIosShareSheet } from '../components/IosInstantInstall';

export default function InstallAppPage() {
  const [mode, setMode] = useState(() => getLaunchAppMode());
  const [canPrompt, setCanPrompt] = useState(false);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const ios = isIosDevice();

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
    setBusy(true);
    setStatus('Checking install…');
    const outcome = await promptPwaInstall();
    setBusy(false);
    if (outcome === 'accepted') {
      setStatus('Installed. Open Reg Guard from your home screen.');
      return;
    }
    if (outcome === 'dismissed') {
      setStatus('Install was dismissed. You can still add it from the browser menu.');
      return;
    }
    setStatus('Use your browser menu → Install app / Add to Home screen.');
  };

  const iosInstallNow = async () => {
    setBusy(true);
    setStatus('');
    const result = await openIosShareSheet();
    setBusy(false);
    if (result === 'shared') {
      setStatus('Next: in Share, tap Add to Home Screen, then Add.');
      return;
    }
    if (result === 'cancelled') {
      setStatus('Share closed — tap Install now again when ready.');
      return;
    }
    setStatus(
      'Tap Share in Safari’s toolbar (square with arrow) → Add to Home Screen → Add.'
    );
  };

  if (ios) {
    return (
      <div className="mx-auto max-w-lg px-4 py-8 text-slate-200">
        <IosInstantInstall forceOpen hideTrigger />
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-xl bg-emerald-500/15 p-3 text-emerald-300">
            {isStandaloneApp() ? (
              <Smartphone className="h-7 w-7" />
            ) : (
              <Share className="h-7 w-7" />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-black text-white">Install Reg Guard</h1>
            <p className="text-sm text-slate-400">Fastest path on iPhone Safari</p>
          </div>
        </div>

        {status ? (
          <p className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
            {status}
          </p>
        ) : null}

        {!isStandaloneApp() && (
          <button
            type="button"
            onClick={() => void iosInstallNow()}
            disabled={busy}
            className="mb-4 w-full min-h-[56px] rounded-xl bg-emerald-600 px-4 py-3 text-lg font-bold text-white hover:bg-emerald-500 inline-flex items-center justify-center gap-2"
          >
            <Share className="h-5 w-5" />
            {busy ? 'Opening Share…' : 'Install now'}
          </button>
        )}

        <ol className="mb-6 list-none space-y-3 text-[15px] leading-relaxed text-slate-300">
          <li className="flex gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-bold text-emerald-300">
              1
            </span>
            <span>
              Tap <strong className="text-emerald-300">Install now</strong> — opens Share
            </span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-bold text-emerald-300">
              2
            </span>
            <span className="inline-flex flex-wrap items-center gap-1">
              Scroll → <strong className="text-emerald-300">Add to Home Screen</strong>
              <PlusSquare className="h-4 w-4 text-emerald-300" aria-hidden />
            </span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-bold text-emerald-300">
              3
            </span>
            <span>
              Tap <strong className="text-emerald-300">Add</strong>, then open Reg Guard from Home
              Screen
            </span>
          </li>
        </ol>

        <button
          type="button"
          onClick={() => void repairPwaInstall(true)}
          className="w-full min-h-[48px] rounded-xl border border-slate-600 px-4 py-3 text-sm font-semibold text-slate-200 hover:bg-slate-800"
        >
          Repair app (clear cache &amp; reload)
        </button>
      </div>
    );
  }

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

      <button
        type="button"
        onClick={() => void repairPwaInstall(true)}
        className="w-full min-h-[48px] rounded-xl border border-slate-600 px-4 py-3 text-sm font-semibold text-slate-200 hover:bg-slate-800"
      >
        Repair app (clear cache &amp; reload)
      </button>
    </div>
  );
}
