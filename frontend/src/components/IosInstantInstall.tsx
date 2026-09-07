/**
 * iPhone Home Screen install helper.
 * On iOS 26, navigator.share() often hangs — so we do NOT wait on it.
 * Primary path: point user at Safari’s real Share button → Add to Home Screen.
 */
import { useEffect, useState } from 'react';
import { Share, X, ExternalLink } from 'lucide-react';
import { isIosDevice, isStandaloneApp } from '../pwaInstall';
import './ios-instant-install.css';

const DISMISS_KEY = 'rg_ios_download_dismissed_v4';

function isLikelyInAppBrowser(): boolean {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent || '';
  return /FBAN|FBAV|Instagram|Line\/|LinkedInApp|TikTok/i.test(ua);
}

/**
 * Best-effort Share open. Always races a timeout so UI never sticks on "Opening…".
 */
export async function openIosShareSheet(): Promise<'shared' | 'unsupported' | 'cancelled'> {
  if (typeof navigator === 'undefined' || typeof navigator.share !== 'function') {
    return 'unsupported';
  }
  const url = window.location.origin + '/';
  const sharePromise = (async () => {
    try {
      await navigator.share({ url });
      return 'shared' as const;
    } catch (err) {
      if (err && typeof err === 'object' && 'name' in err && (err as { name: string }).name === 'AbortError') {
        return 'cancelled' as const;
      }
      try {
        await navigator.share({ title: 'Reg Guard', url });
        return 'shared' as const;
      } catch (err2) {
        if (
          err2 &&
          typeof err2 === 'object' &&
          'name' in err2 &&
          (err2 as { name: string }).name === 'AbortError'
        ) {
          return 'cancelled' as const;
        }
        return 'unsupported' as const;
      }
    }
  })();

  // iOS 26 often never resolves navigator.share — don't block the UI.
  const timed = await Promise.race([
    sharePromise,
    new Promise<'unsupported'>((resolve) => {
      window.setTimeout(() => resolve('unsupported'), 1500);
    }),
  ]);
  return timed;
}

export async function instantIosInstall(): Promise<'shared' | 'unsupported' | 'cancelled' | 'skipped'> {
  if (!isIosDevice() || isStandaloneApp()) return 'skipped';
  return openIosShareSheet();
}

type Props = {
  forceShow?: boolean;
};

/**
 * Bottom bar: tells user to use Safari Share (reliable on iOS 26).
 * Optional quick Share attempt, but never stays stuck on Opening….
 */
export default function IosInstantInstall({ forceShow = false }: Props) {
  const [eligible, setEligible] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState(
    'Tap Safari Share (□↑) below → Add to Home Screen'
  );
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

  const onHelpTap = async () => {
    setBusy(true);
    setHint('Tap Safari Share (□↑) at the bottom → scroll → Add to Home Screen');
    try {
      await openIosShareSheet();
    } finally {
      // Always clear — never leave "Opening…" stuck (iOS 26 hang).
      setBusy(false);
      setHint('Safari Share (□↑) → View More → Add to Home Screen → Add');
    }
  };

  return (
    <div className="ios-download-bar" role="dialog" aria-label="Add Reg Guard to Home Screen">
      <div className="ios-download-bar-inner">
        <div className="ios-download-copy">
          <p className="ios-download-title">Add to Home Screen</p>
          <p className="ios-download-sub">
            {inApp
              ? 'Open this page in the Safari app first'
              : hint}
          </p>
        </div>
        {!inApp ? (
          <button
            type="button"
            className="ios-download-btn"
            onClick={() => void onHelpTap()}
            disabled={busy}
          >
            <Share size={18} />
            {busy ? '…' : 'How'}
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
