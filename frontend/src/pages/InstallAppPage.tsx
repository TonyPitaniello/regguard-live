/**
 * /install — single Download button that fires the native install / iOS Share.
 * No instruction lists, no secondary CTAs.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Smartphone } from 'lucide-react';
import { isStandaloneApp, oneClickInstallApp } from '../pwaInstall';

export default function InstallAppPage() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (busy) return;
    setBusy(true);
    await oneClickInstallApp();
    setBusy(false);
  };

  useEffect(() => {
    if (isStandaloneApp()) {
      navigate('/', { replace: true });
      return;
    }
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isStandaloneApp()) return null;

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center px-4 py-12 text-center">
      <div className="rounded-xl bg-emerald-500/15 p-4 text-emerald-300 mb-4">
        <Download className="h-8 w-8" />
      </div>
      <h1 className="text-2xl font-black text-white mb-6">Download Reg Guard</h1>
      <button
        type="button"
        onClick={() => void run()}
        disabled={busy}
        className="w-full max-w-sm min-h-[56px] rounded-xl bg-emerald-600 px-6 py-4 text-lg font-bold text-white hover:bg-emerald-500 inline-flex items-center justify-center gap-2 disabled:opacity-70"
      >
        {busy ? <Smartphone className="h-5 w-5 animate-pulse" /> : <Download className="h-5 w-5" />}
        {busy ? 'Opening…' : 'Download'}
      </button>
    </div>
  );
}
