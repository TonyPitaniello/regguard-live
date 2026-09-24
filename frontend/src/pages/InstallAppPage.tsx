/**
 * Install page — one-tap Download triggers native install (Chrome) or iOS Share.
 */
import { useEffect, useState } from 'react';
import { Download, Smartphone, Share, PlusSquare } from 'lucide-react';
import {
  getDeferredInstallPrompt,
  getLaunchAppMode,
  isIosDevice,
  isStandaloneApp,
  oneClickInstallApp,
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
      return;
    }
    // Auto one-click when Chromium already has a deferred prompt
    if (getDeferredInstallPrompt()) {
      void tryNativeInstall();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tryNativeInstall = async () => {
    setBusy(true);
    setStatus('Opening install…');
    const outcome = await oneClickInstallApp();
    setBusy(false);
    if (outcome === 'accepted' || outcome === 'already_installed') {
      setStatus('Installed. Open Reg Guard from your home screen.');
      return;
    }
    if (outcome === 'dismissed') {
      setStatus('Install was dismissed. Tap Download to try again.');
      return;
    }
    if (outcome === 'ios_share' || outcome === 'ios_help') {
      setStatus('Next: tap Add to Home Screen, then Add.');
      return;
    }
    setStatus('Use your browser menu → Install app / Add to Home screen.');
  };

  const iosDownload = async () => {
    setBusy(true);
    setStatus('');
    const result = await openIosShareSheet();
    setBusy(false);
    if (result === 'shared') {
      setStatus('Next: tap Add to Home Screen, then Add.');
      return;
    }
    if (result === 'cancelled') {
      setStatus('Tap Download again when ready.');
      return;
    }
    setStatus('Use Safari Share (□↑) → Add to Home Screen → Add.');
  };

  if (ios) {
    return (
      <div className="mx-auto max-w-lg px-4 py-8 text-slate-200 pb-28">
        <IosInstantInstall forceShow forceSteps />
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-xl bg-emerald-500/15 p-3 text-emerald-300">
            {isStandaloneApp() ? (
              <Smartphone className="h-7 w-7" />
            ) : (
              <Download className="h-7 w-7" />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-black text-white">Download Reg Guard</h1>
            <p className="text-sm text-slate-400">One tap opens Share on iPhone Safari</p>
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
            onClick={() => void iosDownload()}
            disabled={busy}
            className="mb-4 w-full min-h-[56px] rounded-xl bg-emerald-600 px-4 py-3 text-lg font-bold text-white hover:bg-emerald-500 inline-flex items-center justify-center gap-2"
          >
            <Download className="h-5 w-5" />
            {busy ? 'Opening…' : 'Download'}
          </button>
        )}

        <ol className="mb-6 list-none space-y-3 text-[15px] leading-relaxed text-slate-300">
          <li className="flex gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-bold text-emerald-300">
              1
            </span>
            <span>
              Tap <strong className="text-emerald-300">Download</strong> (opens Share)
            </span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-bold text-emerald-300">
              2
            </span>
            <span className="inline-flex flex-wrap items-center gap-1">
              Tap <strong className="text-emerald-300">Add to Home Screen</strong>
              <PlusSquare className="h-4 w-4 text-emerald-300" aria-hidden />
            </span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-bold text-emerald-300">
              3
            </span>
            <span>
              Tap <strong className="text-emerald-300">Add</strong>, then open from Home Screen
            </span>
          </li>
        </ol>

        <p className="mb-4 text-xs text-slate-500 inline-flex items-center gap-1">
          <Share className="h-3.5 w-3.5" />
          Apple requires Share → Add to Home Screen (no silent install in Safari).
        </p>

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
          <h1 className="text-2xl font-black text-white">Download Reg Guard</h1>
          <p className="text-sm text-slate-400">One tap installs to your home screen</p>
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
          onClick={() => void tryNativeInstall()}
          disabled={busy}
          className="mb-4 w-full min-h-[56px] rounded-xl bg-emerald-600 px-4 py-3 text-lg font-bold text-white hover:bg-emerald-500 inline-flex items-center justify-center gap-2"
        >
          <Download className="h-5 w-5" />
          {busy ? 'Opening…' : canPrompt || mode === 'prompt' ? 'Download Reg Guard' : 'Download Reg Guard'}
        </button>
      )}

      {!canPrompt && !isStandaloneApp() ? (
        <p className="mb-4 text-sm text-slate-400 leading-relaxed">
          If the install dialog does not appear, use the browser menu →{' '}
          <strong className="text-emerald-300">Install app</strong> /{' '}
          <strong className="text-emerald-300">Add to Home screen</strong>.
        </p>
      ) : null}

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
