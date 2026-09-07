/**
 * iPhone Home Screen install — show clear Safari Share steps on-device.
 * iOS 26: Share is often behind ⋯; Add to Home Screen may need View More.
 * navigator.share often hangs — instructions are the primary UX.
 */
import { useEffect, useState } from 'react';
import { Share, X, ExternalLink, Smartphone } from 'lucide-react';
import { isIosDevice, isStandaloneApp } from '../pwaInstall';
import './ios-instant-install.css';

const DISMISS_KEY = 'rg_ios_download_dismissed_v5';
const STEPS_SEEN_KEY = 'rg_ios_steps_seen_v1';

function isLikelyInAppBrowser(): boolean {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent || '';
  return /FBAN|FBAV|Instagram|Line\/|LinkedInApp|TikTok/i.test(ua);
}

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
      return 'unsupported' as const;
    }
  })();
  return Promise.race([
    sharePromise,
    new Promise<'unsupported'>((resolve) => {
      window.setTimeout(() => resolve('unsupported'), 1200);
    }),
  ]);
}

/** Opens instruction sheet via custom event (PlatformLayout / Download). */
export function showIosInstallInstructions(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent('rg-ios-install-help'));
}

export async function instantIosInstall(): Promise<'shared' | 'unsupported' | 'cancelled' | 'skipped'> {
  if (!isIosDevice() || isStandaloneApp()) return 'skipped';
  showIosInstallInstructions();
  return 'unsupported';
}

type Props = {
  forceShow?: boolean;
  /** Open the full step sheet immediately (e.g. /install). */
  forceSteps?: boolean;
};

function IosStepsSheet({
  inApp,
  onClose,
}: {
  inApp: boolean;
  onClose: () => void;
}) {
  return (
    <div
      className="ios-steps-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="How to add Reg Guard to Home Screen"
      onClick={onClose}
    >
      <div className="ios-steps-sheet" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="ios-steps-close" onClick={onClose} aria-label="Close">
          <X size={22} />
        </button>
        <div className="ios-steps-icon">
          <Smartphone size={28} />
        </div>
        <h2>Add Reg Guard to Home Screen</h2>
        <p className="ios-steps-lead">
          Apple requires Safari&apos;s Share menu. Our Download button cannot install the app by
          itself on iPhone.
        </p>

        {inApp ? (
          <div className="ios-steps-warn">
            <ExternalLink size={18} />
            <div>
              <strong>Open in Safari first</strong>
              <span>This in-app browser blocks Home Screen install. Tap ··· → Open in Safari.</span>
            </div>
          </div>
        ) : (
          <ol className="ios-steps-list">
            <li>
              <span className="ios-steps-num">1</span>
              <span>
                Stay in the <strong>Safari</strong> app (compass icon)
              </span>
            </li>
            <li>
              <span className="ios-steps-num">2</span>
              <span>
                Tap <strong>Share</strong> (□↑) at the bottom — or tap <strong>⋯</strong> then Share
                (iOS 26 Compact)
              </span>
            </li>
            <li>
              <span className="ios-steps-num">3</span>
              <span>
                Tap <strong>View More</strong> if needed, then <strong>Add to Home Screen</strong>
              </span>
            </li>
            <li>
              <span className="ios-steps-num">4</span>
              <span>
                Tap <strong>Add</strong>. Leave <strong>Open as Web App</strong> on if you see it
              </span>
            </li>
          </ol>
        )}

        <p className="ios-steps-tip">
          Still missing? Settings → Apps → Safari → Tabs → choose <strong>Bottom</strong> (not
          Compact), force-close Safari, then try again.
        </p>

        <button type="button" className="ios-steps-done" onClick={onClose}>
          Got it — I&apos;ll use Share
        </button>
      </div>
    </div>
  );
}

export default function IosInstantInstall({ forceShow = false, forceSteps = false }: Props) {
  const [eligible, setEligible] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [stepsOpen, setStepsOpen] = useState(false);
  const inApp = isLikelyInAppBrowser();

  useEffect(() => {
    if (!isIosDevice() || isStandaloneApp()) {
      setEligible(false);
      return;
    }
    setEligible(true);
    if (forceShow) setHidden(false);
    else {
      try {
        if (sessionStorage.getItem(DISMISS_KEY) === '1') setHidden(true);
      } catch {
        /* ignore */
      }
    }
    if (forceSteps) {
      setStepsOpen(true);
      return;
    }
    try {
      if (sessionStorage.getItem(STEPS_SEEN_KEY) !== '1') {
        setStepsOpen(true);
        sessionStorage.setItem(STEPS_SEEN_KEY, '1');
      }
    } catch {
      setStepsOpen(true);
    }
  }, [forceShow, forceSteps]);

  useEffect(() => {
    const onHelp = () => {
      if (!isIosDevice() || isStandaloneApp()) return;
      setHidden(false);
      setStepsOpen(true);
    };
    window.addEventListener('rg-ios-install-help', onHelp);
    return () => window.removeEventListener('rg-ios-install-help', onHelp);
  }, []);

  if (!eligible) return null;

  const dismissBar = () => {
    setHidden(true);
    try {
      sessionStorage.setItem(DISMISS_KEY, '1');
    } catch {
      /* ignore */
    }
  };

  const closeSteps = () => setStepsOpen(false);

  return (
    <>
      {stepsOpen && <IosStepsSheet inApp={inApp} onClose={closeSteps} />}

      {!hidden && (
        <div className="ios-download-bar" role="dialog" aria-label="Add Reg Guard to Home Screen">
          <div className="ios-download-bar-inner">
            <div className="ios-download-copy">
              <p className="ios-download-title">Add to Home Screen</p>
              <p className="ios-download-sub">
                {inApp
                  ? 'Open in Safari first'
                  : 'Safari Share (□↑) → Add to Home Screen'}
              </p>
            </div>
            <button
              type="button"
              className="ios-download-btn"
              onClick={() => setStepsOpen(true)}
            >
              <Share size={18} />
              Steps
            </button>
            <button type="button" className="ios-download-x" onClick={dismissBar} aria-label="Dismiss">
              <X size={18} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
