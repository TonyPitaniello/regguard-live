/**
 * One-tap iPhone install: button → Safari Share sheet (Add to Home Screen).
 * Apple blocks fully automatic PWA install; Share is the fastest legal path.
 */
import { useEffect, useState } from 'react';
import { Download, X, ExternalLink } from 'lucide-react';
import { isIosDevice, isStandaloneApp } from '../pwaInstall';
import './ios-instant-install.css';

const DISMISS_KEY = 'rg_ios_download_dismissed_v3';

function isLikelyInAppBrowser(): boolean {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent || '';
  return /FBAN|FBAV|Instagram|Line\/|LinkedInApp|TikTok/i.test(ua);
}

/**
 * Opens iOS Share with a minimal payload so system actions
 * (including Add to Home Screen) are more likely to appear.
 */
export async function openIosShareSheet(): Promise<'shared' | 'unsupported' | 'cancelled'> {
  if (typeof navigator === 'undefined' || typeof navigator.share !== 'function') {
    return 'unsupported';
  }
  const url = window.location.origin + '/';
  try {
    // Minimal share = more system actions (A2HS) vs custom text-only shares.
    await navigator.share({ url });
    return 'shared';
  } catch (err) {
    if (err && typeof err === 'object' && 'name' in err && (err as { name: string }).name === 'AbortError') {
      return 'cancelled';
    }
    try {
      await navigator.share({
        title: 'Reg Guard',
        url,
      });
      return 'shared';
    } catch (err2) {
      if (
        err2 &&
        typeof err2 === 'object' &&
        'name' in err2 &&
        (err2 as { name: string }).name === 'AbortError'
      ) {
        return 'cancelled';
      }
      return 'unsupported';
    }
  }
}

/** Call from Get app / Launch app — instant Share, no modal. */
export async function instantIosInstall(): Promise<'shared' | 'unsupported' | 'cancelled' | 'skipped'> {
  if (!isIosDevice() || isStandaloneApp()) return 'skipped';
  return openIosShareSheet();
}

type Props = {
  /** Force-show the bottom download bar (e.g. /install). */
  forceShow?: boolean;
};

/**
 * Persistent one-tap Download bar on iPhone Safari — like the old Launch app banner.
 * Tap → Share sheet immediately (no intermediate coach screen).
 */
export default function IosInstantInstall({ forceShow = false }: Props) {
  const [eligible, setEligible] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState('');
  const inApp = isLikelyInAppBrowser();

  useEffect(() => {
    if (!isIosDevice() || isStandaloneApp()) {
      setEligible(false);
      return;
    }
    setEligible(true);
    if (forceShow) {
      setHidden(false);
      return;
    }
    try {
      if (sessionStorage.getItem(DISMISS_KEY) === '1') setHidden(true);
    } catch {
      /* ignore */
    }
  }, [forceShow]);

  if (!eligible || hidden) return null;

  const dismiss = () => {
    setHidden(true);
    try {
      sessionStorage.setItem(DISMISS_KEY, '1');
    } catch {
      /* ignore */
    }
  };

  const downloadNow = async () => {
    setBusy(true);
    setHint('');
    const result = await openIosShareSheet();
    setBusy(false);
    if (result === 'shared') {
      setHint('Next: tap Add to Home Screen → Add');
      return;
    }
    if (result === 'cancelled') {
      setHint('Tap Download again when ready');
      return;
    }
    setHint('Use Safari Share (□↑) → Add to Home Screen');
  };

  return (
    <div className="ios-download-bar" role="dialog" aria-label="Download Reg Guard">
      <div className="ios-download-bar-inner">
        <div className="ios-download-copy">
          <p className="ios-download-title">Download Reg Guard</p>
          <p className="ios-download-sub">
            {inApp
              ? 'Open in Safari first, then tap Download'
              : hint || 'One tap → Add to Home Screen'}
          </p>
        </div>
        {!inApp ? (
          <button
            type="button"
            className="ios-download-btn"
            onClick={() => void downloadNow()}
            disabled={busy}
          >
            <Download size={18} />
            {busy ? 'Opening…' : 'Download'}
          </button>
        ) : (
          <span className="ios-download-inapp">
            <ExternalLink size={16} />
            Safari
          </span>
        )}
        <button type="button" className="ios-download-x" onClick={dismiss} aria-label="Dismiss">
          <X size={18} />
        </button>
      </div>
    </div>
  );
}
