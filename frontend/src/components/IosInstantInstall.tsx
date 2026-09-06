/**
 * Closest thing to one-tap install on iPhone:
 * Apple blocks programmatic A2HS, so we open the system Share sheet
 * (navigator.share) where "Add to Home Screen" lives — one tap from our UI.
 */
import { useEffect, useState } from 'react';
import { Share, PlusSquare, X, Smartphone, ExternalLink } from 'lucide-react';
import {
  isIosDevice,
  isStandaloneApp,
} from '../pwaInstall';
import './ios-instant-install.css';

const DISMISS_KEY = 'rg_ios_install_dismissed_v2';

function isLikelyInAppBrowser(): boolean {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent || '';
  // Facebook / Instagram / TikTok / LinkedIn in-app browsers block A2HS.
  if (/FBAN|FBAV|Instagram|Line\/|LinkedInApp|TikTok/i.test(ua)) return true;
  return false;
}

async function openIosShareSheet(): Promise<'shared' | 'unsupported' | 'cancelled'> {
  if (typeof navigator === 'undefined' || typeof navigator.share !== 'function') {
    return 'unsupported';
  }
  try {
    await navigator.share({
      title: 'Reg Guard',
      text: 'Add Reg Guard to your Home Screen for one-tap Bid Risk Receipts.',
      url: window.location.origin + '/',
    });
    return 'shared';
  } catch (err) {
    // User cancelled share sheet
    if (err && typeof err === 'object' && 'name' in err && (err as { name: string }).name === 'AbortError') {
      return 'cancelled';
    }
    return 'unsupported';
  }
}

type Props = {
  /** When true, open immediately (e.g. /install or Get app). */
  forceOpen?: boolean;
  /** Hide the floating trigger; only show the sheet when open. */
  hideTrigger?: boolean;
};

export default function IosInstantInstall({ forceOpen = false, hideTrigger = false }: Props) {
  const [eligible, setEligible] = useState(false);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState('');
  const inApp = isLikelyInAppBrowser();

  useEffect(() => {
    if (!isIosDevice() || isStandaloneApp()) {
      setEligible(false);
      return;
    }
    setEligible(true);

    if (forceOpen) {
      setOpen(true);
      return;
    }

    try {
      if (sessionStorage.getItem(DISMISS_KEY) === '1') return;
    } catch {
      /* ignore */
    }
    // Auto-present once per session so install feels instant on first open.
    const t = window.setTimeout(() => setOpen(true), 600);
    return () => window.clearTimeout(t);
  }, [forceOpen]);

  if (!eligible) return null;

  const dismiss = () => {
    setOpen(false);
    try {
      sessionStorage.setItem(DISMISS_KEY, '1');
    } catch {
      /* ignore */
    }
  };

  const installNow = async () => {
    setBusy(true);
    setHint('');
    const result = await openIosShareSheet();
    setBusy(false);
    if (result === 'shared') {
      setHint('In the Share sheet: scroll and tap Add to Home Screen, then Add.');
      return;
    }
    if (result === 'cancelled') {
      setHint('Share was closed. Tap Install again, or use the Share icon in Safari’s toolbar.');
      return;
    }
    setHint(
      'Tap the Share icon in Safari’s bottom toolbar (square with arrow) → Add to Home Screen → Add.'
    );
  };

  return (
    <>
      {!hideTrigger && !open && (
        <button
          type="button"
          className="ios-install-fab"
          onClick={() => setOpen(true)}
          aria-label="Install Reg Guard"
        >
          <Smartphone size={18} />
          Install
        </button>
      )}

      {open && (
        <div className="ios-install-overlay" role="dialog" aria-modal="true" aria-label="Install Reg Guard">
          <div className="ios-install-sheet">
            <button type="button" className="ios-install-close" onClick={dismiss} aria-label="Close">
              <X size={22} />
            </button>

            <div className="ios-install-mark">RG</div>
            <h2>Install Reg Guard</h2>
            <p className="ios-install-sub">
              One tap opens Share — then Add to Home Screen. Apple does not allow fully automatic
              install in Safari.
            </p>

            {inApp ? (
              <div className="ios-install-warn">
                <ExternalLink size={18} />
                <div>
                  <strong>Open in Safari first</strong>
                  <span>
                    In-app browsers (Mail, Instagram, etc.) block Home Screen install. Tap ··· →
                    Open in Safari, then come back here.
                  </span>
                </div>
              </div>
            ) : (
              <button
                type="button"
                className="ios-install-primary"
                onClick={() => void installNow()}
                disabled={busy}
              >
                <Share size={20} />
                {busy ? 'Opening Share…' : 'Install now'}
              </button>
            )}

            {hint ? <p className="ios-install-hint">{hint}</p> : null}

            <ol className="ios-install-steps">
              <li>
                <span className="ios-step-num">1</span>
                <span>
                  Tap <strong>Install now</strong> (opens Share)
                </span>
              </li>
              <li>
                <span className="ios-step-num">2</span>
                <span>
                  Scroll → <strong>Add to Home Screen</strong>
                  <PlusSquare className="ios-inline-icon" size={16} aria-hidden />
                </span>
              </li>
              <li>
                <span className="ios-step-num">3</span>
                <span>
                  Tap <strong>Add</strong>, then open <strong>Reg Guard</strong> from your Home Screen
                </span>
              </li>
            </ol>

            <div className="ios-safari-hint" aria-hidden>
              <div className="ios-safari-bar">
                <span className="ios-safari-glow" />
                <Share size={18} />
                <span>Share is in Safari’s toolbar</span>
              </div>
            </div>

            <button type="button" className="ios-install-later" onClick={dismiss}>
              Not now
            </button>
          </div>
        </div>
      )}
    </>
  );
}

/** Call from Get app / Launch app buttons. */
export { openIosShareSheet };
