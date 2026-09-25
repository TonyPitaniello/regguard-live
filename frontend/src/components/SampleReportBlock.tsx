/**
 * Sample tier artifacts — Fort Worth Chapin DC-adjacent site at every tier.
 * List = view only. Forward / Download live in the in-app viewer.
 */

import { useState, type MouseEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { HABIT_TIERS } from '../habitDeliverableLadder';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';
import { viewInAppUrl } from '../openAndDownload';
import { PRODUCT_COPY } from '../productCopy';

const VIEW_BTN_CLASS =
  'inline-flex items-center justify-center min-h-[44px] px-5 rounded-lg font-bold text-sm transition disabled:opacity-60 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white border border-emerald-400/30 shadow-md shadow-green-500/20';

/** Same-origin static samples under /public/sample */
export function sampleUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  if (p.startsWith('/sample/')) return p;
  return `/sample${p.startsWith('/') ? p : `/${p}`}`;
}

function sampleFilename(path: string): string {
  const base = path.split('/').pop() || 'sample.bin';
  const map: Record<string, string> = {
    'tier-ladder.pdf': 'RegGuard_Sample_Tier_Ladder.pdf',
    'free-preview.pdf': 'RegGuard_Sample_Free_Preview.pdf',
    'partner-receipt.pdf': 'RegGuard_Sample_Full_Bid_Risk_Receipt.pdf',
    'pro-desk-report.pdf': 'RegGuard_Sample_Contractor_Pro_Report.pdf',
    'pro-desk.zip': 'RegGuard_Sample_Pro_Desk.zip',
    'ic-project-report.pdf': 'RegGuard_Sample_IC_Project_Report.pdf',
    'ic-diligence-bundle.zip': 'RegGuard_Sample_IC_Diligence_Bundle.zip',
    'executive-summary.pdf': 'RegGuard_Sample_Executive_Summary.pdf',
    'plano-punch-list.pdf': 'RegGuard_Sample_Estimator_Receipt.pdf',
  };
  return map[base] || `RegGuard_Sample_${base}`;
}

type SampleRowDef = {
  /** Stable key / default path */
  href: string;
  /** In-app React route to open on View (scrollable live results UI) */
  viewRoute?: string;
  /** Scrollable in-app file (defaults to href). Prefer ZIP when package exists. */
  viewHref?: string;
  title: string;
  subtitle: string;
  price: string | null;
  highlight?: boolean;
};

/**
 * Samples in product order — Free → Estimator → Pro → IC.
 * Site Diligence Results + Executive Summary live inside each tier viewer (not listed here).
 */
export const SAMPLE_ROWS: readonly SampleRowDef[] = [
  {
    href: '/sample-site-diligence?tier=free',
    viewRoute: '/sample-site-diligence?tier=free',
    title: HABIT_TIERS.free.name,
    subtitle:
      'Soft-locked Bid Risk Receipt preview — stamp + top 5 punch lines. Forward unlocks a bit more; Estimator unlocks the full habit.',
    price: HABIT_TIERS.free.priceLabel,
  },
  {
    href: '/sample-site-diligence?tier=partner',
    viewRoute: '/sample-site-diligence?tier=partner',
    title: HABIT_TIERS.partner.name,
    subtitle:
      'Full forwardable Bid Risk Receipt + unlocked punch + Saved Jobs. Fee dollars and City Pack PDF stay on Pro.',
    price: `${HABIT_TIERS.partner.priceLabel}/mo`,
  },
  {
    href: '/sample-site-diligence?tier=pro',
    viewRoute: '/sample-site-diligence?tier=pro',
    title: HABIT_TIERS.contractor_pro.name,
    subtitle:
      'Deep scout + fee dollars + Full City Pack PDF, fee/punch CSV, and bid packet — the bid-week desk.',
    price: `${HABIT_TIERS.contractor_pro.priceLabel}/mo`,
  },
  {
    href: '/sample/ic-diligence-bundle.zip',
    title: IC_BUNDLE.tierName,
    subtitle: `Counsel ZIP beyond Pro — decision memo, boardroom PDF, DOCX, and Excel evidence for one site`,
    price: IC_BUNDLE.priceLabel,
  },
] as const;

/** @deprecated — use SAMPLE_ROWS */
export const SAMPLE_DOWNLOADS = SAMPLE_ROWS.filter((r) => !r.highlight).map((r) => ({
  tier: r.title,
  price: r.price || '',
  href: r.href,
  shortLabel: r.subtitle,
  detail: r.subtitle,
}));

/** View only — Forward / Download are inside the viewer. */
export function SampleOpenButton({
  href,
  viewRoute,
  viewHref,
  label,
  className,
}: {
  href: string;
  viewRoute?: string;
  viewHref?: string;
  /** @deprecated ignored — downloads happen in the viewer */
  downloadHref?: string;
  label?: string;
  className?: string;
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const viewPath = viewHref || href;
  const title = label || sampleFilename(viewPath).replace(/^RegGuard_/, '').replace(/_/g, ' ');

  const runView = async (e?: MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setBusy(true);
    setErr('');
    try {
      if (viewRoute) {
        navigate(viewRoute);
        return;
      }
      const url = sampleUrl(viewPath);
      const name = sampleFilename(viewPath);
      await viewInAppUrl(url, name, { navigate: (to) => navigate(to) });
    } catch (errObj) {
      setErr(errObj instanceof Error ? errObj.message : 'Could not open');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`w-full md:w-auto md:shrink-0 ${className || ''}`}>
      <button
        type="button"
        title={`View ${title}`}
        aria-label={`View ${title}`}
        onClick={(e) => void runView(e)}
        disabled={busy}
        className={`w-full md:w-auto ${VIEW_BTN_CLASS}`}
      >
        {busy ? <Loader2 className="w-5 h-5 animate-spin shrink-0" /> : 'View'}
      </button>
      {err ? <p className="text-amber-200 text-xs mt-1 text-center md:text-left">{err}</p> : null}
    </div>
  );
}

function SampleRow(row: SampleRowDef) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const open = async () => {
    if (busy) return;
    setBusy(true);
    try {
      if (row.viewRoute) {
        navigate(row.viewRoute);
        return;
      }
      const path = row.viewHref || row.href;
      await viewInAppUrl(sampleUrl(path), sampleFilename(path), {
        navigate: (to) => navigate(to),
      });
    } catch {
      /* SampleOpenButton shows errors if used; row click is best-effort */
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={() => void open()}
      disabled={busy}
      className={`w-full text-left flex flex-col gap-3 rounded-xl border p-3.5 md:p-4 md:flex-row md:items-center md:gap-4 transition hover:border-emerald-400/50 disabled:opacity-60 ${
        row.highlight
          ? 'border-emerald-500/35 bg-emerald-500/10'
          : 'border-[rgba(61,79,143,0.4)] bg-[rgba(10,20,41,0.85)]'
      }`}
    >
      <div className="min-w-0 flex-1">
        <p className="text-white font-bold text-[15px] md:text-base leading-snug break-words">
          {row.title}
        </p>
        {row.price ? (
          <p className="text-emerald-300 font-semibold text-sm mt-0.5">{row.price}</p>
        ) : null}
        {row.subtitle ? (
          <p className="text-[#b8c1d1] text-xs md:text-sm mt-1 leading-relaxed break-words">
            {row.subtitle}
          </p>
        ) : null}
      </div>
      <span className={`${VIEW_BTN_CLASS} shrink-0 pointer-events-none`}>
        {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : 'View'}
      </span>
    </button>
  );
}

export function SampleReportBlock({
  compact = false,
  id = 'sample-report',
}: {
  compact?: boolean;
  id?: string;
}) {
  return (
    <div id={id} className="text-left w-full max-w-full overflow-hidden">
      <p className="text-amber-300 text-xs font-bold tracking-wide mb-2">
        {PRODUCT_COPY.sampleEyebrow}
      </p>
      <p
        className={
          compact
            ? 'text-emerald-300 text-sm font-semibold mb-1.5'
            : 'text-emerald-300 text-base sm:text-lg font-semibold mb-2'
        }
      >
        {PRODUCT_COPY.sampleLead}
      </p>
      <h3
        className={
          compact
            ? 'text-xl sm:text-2xl font-black text-white mb-2 leading-tight'
            : 'text-3xl sm:text-5xl font-black text-white mb-3 leading-tight'
        }
      >
        {PRODUCT_COPY.sampleHeading}
      </h3>
      <p className="text-[#b8c1d1] text-sm leading-relaxed mb-4 break-words">
        9999 Chapin School Road, Fort Worth, TX 76126 — large-load / DC-adjacent screening with live
        Fort Worth Development Services cites. {PRODUCT_COPY.honestyShort}
      </p>

      <div className="space-y-2.5 md:space-y-3">
        {SAMPLE_ROWS.map((row) => (
          <SampleRow key={row.href} {...row} />
        ))}
      </div>
    </div>
  );
}
