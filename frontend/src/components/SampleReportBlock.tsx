/**
 * Sample tier downloads — Fort Worth Chapin DC-adjacent site at every tier.
 * Includes Site Diligence Results (on-screen panel) + Executive Summary.
 */

import { useState, type MouseEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Eye, Loader2 } from 'lucide-react';
import { HABIT_TIERS } from '../habitDeliverableLadder';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';
import { downloadOnlyUrl, viewInAppUrl } from '../openAndDownload';
import { PRODUCT_COPY } from '../productCopy';

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
  /** Scrollable in-app PDF (defaults to href) */
  viewHref?: string;
  /** Disk download (defaults to href) */
  downloadHref?: string;
  title: string;
  subtitle: string;
  price: string | null;
  highlight?: boolean;
};

/**
 * Samples in product order:
 * 1) On-screen results panel after address entry
 * 2) Executive summary card from that panel
 * 3) Tier artifacts
 */
export const SAMPLE_ROWS: readonly SampleRowDef[] = [
  {
    href: '/sample-site-diligence',
    viewRoute: '/sample-site-diligence',
    downloadHref: '/sample/executive-summary.pdf',
    title: PRODUCT_COPY.resultsPanelTitle,
    subtitle:
      'The long scrollable results panel after you enter an address — stamp, contingency, punch, and packs',
    price: null,
    highlight: true,
  },
  {
    href: '/sample/executive-summary.pdf',
    title: PRODUCT_COPY.executiveSummary,
    subtitle: `The amber summary card at the top of ${PRODUCT_COPY.resultsPanelTitle}`,
    price: null,
    highlight: true,
  },
  {
    href: '/sample/tier-ladder.pdf',
    title: 'Sample Tier Ladder',
    subtitle: 'All tiers on one Fort Worth site',
    price: null,
  },
  {
    href: '/sample/free-preview.pdf',
    title: HABIT_TIERS.free.name,
    subtitle: 'Sample free Bid Risk Receipt preview PDF',
    price: HABIT_TIERS.free.priceLabel,
  },
  {
    href: '/sample/partner-receipt.pdf',
    title: HABIT_TIERS.partner.name,
    subtitle: 'Sample Bid Risk Receipt PDF',
    price: `${HABIT_TIERS.partner.priceLabel}/mo`,
  },
  {
    href: '/sample/pro-desk.zip',
    viewHref: '/sample/pro-desk-report.pdf',
    downloadHref: '/sample/pro-desk.zip',
    title: HABIT_TIERS.contractor_pro.name,
    subtitle: 'Scrollable sample report · Save downloads the full Pro package ZIP',
    price: `${HABIT_TIERS.contractor_pro.priceLabel}/mo`,
  },
  {
    href: '/sample/ic-diligence-bundle.zip',
    viewHref: '/sample/ic-project-report.pdf',
    downloadHref: '/sample/ic-diligence-bundle.zip',
    title: IC_BUNDLE.tierName,
    subtitle: `Scrollable boardroom sample · Save downloads the full ${IC_BUNDLE.productName} ZIP`,
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

/** Eye = view in app; Download = save. Full-width on phones; icon track on sm+. */
export function SampleOpenButton({
  href,
  viewRoute,
  viewHref,
  downloadHref,
  label,
  className,
}: {
  href: string;
  viewRoute?: string;
  viewHref?: string;
  downloadHref?: string;
  label?: string;
  className?: string;
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState<'view' | 'download' | null>(null);
  const [err, setErr] = useState('');
  const viewPath = viewHref || href;
  const savePath = downloadHref || href;
  const title = label || sampleFilename(viewPath).replace(/^RegGuard_/, '').replace(/_/g, ' ');

  const run = async (mode: 'view' | 'download', e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setBusy(mode);
    setErr('');
    try {
      if (mode === 'view') {
        if (viewRoute) {
          navigate(viewRoute);
          return;
        }
        const url = sampleUrl(viewPath);
        const name = sampleFilename(viewPath);
        await viewInAppUrl(url, name, { navigate: (to) => navigate(to) });
      } else {
        const url = sampleUrl(savePath);
        const name = sampleFilename(savePath);
        await downloadOnlyUrl(url, name);
      }
    } catch (errObj) {
      setErr(errObj instanceof Error ? errObj.message : 'Action failed');
    } finally {
      setBusy(null);
    }
  };

  const btnBase =
    'inline-flex items-center justify-center gap-2 min-h-[44px] rounded-lg font-bold text-sm transition disabled:opacity-60';

  return (
    <div className={`w-full md:w-auto md:shrink-0 ${className || ''}`}>
      <div
        className="grid grid-cols-2 gap-2 w-full md:w-[7.5rem]"
        role="group"
        aria-label={`${title}: view or download`}
      >
        <button
          type="button"
          title={`View ${title} in Reg Guard`}
          aria-label={`View ${title} in Reg Guard`}
          onClick={(e) => void run('view', e)}
          disabled={busy !== null}
          className={`${btnBase} border border-emerald-400/60 bg-[#0f1d38] hover:bg-emerald-500/20 text-emerald-300 px-3 md:px-0`}
        >
          {busy === 'view' ? (
            <Loader2 className="w-5 h-5 animate-spin shrink-0" />
          ) : (
            <Eye className="w-5 h-5 shrink-0" strokeWidth={2.25} />
          )}
          <span className="md:hidden">View</span>
        </button>
        <button
          type="button"
          title={`Download ${title}`}
          aria-label={`Download ${title}`}
          onClick={(e) => void run('download', e)}
          disabled={busy !== null}
          className={`${btnBase} bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white border border-emerald-400/30 shadow-md shadow-green-500/20 px-3 md:px-0`}
        >
          {busy === 'download' ? (
            <Loader2 className="w-5 h-5 animate-spin shrink-0" />
          ) : (
            <Download className="w-5 h-5 shrink-0" strokeWidth={2.25} />
          )}
          <span className="md:hidden">Save</span>
        </button>
      </div>
      {err ? <p className="text-amber-200 text-xs mt-1 text-center md:text-left">{err}</p> : null}
    </div>
  );
}

function SampleRow({
  href,
  viewRoute,
  viewHref,
  downloadHref,
  title,
  subtitle,
  price,
  highlight,
}: SampleRowDef) {
  return (
    <div
      className={`flex flex-col gap-3 rounded-xl border p-3.5 md:p-4 md:flex-row md:items-center md:gap-4 ${
        highlight
          ? 'border-emerald-500/35 bg-emerald-500/10'
          : 'border-[rgba(61,79,143,0.4)] bg-[rgba(10,20,41,0.85)]'
      }`}
    >
      <div className="min-w-0 flex-1">
        <p className="text-white font-bold text-[15px] md:text-base leading-snug break-words">
          {title}
        </p>
        {price ? (
          <p className="text-emerald-300 font-semibold text-sm mt-0.5">{price}</p>
        ) : null}
        {subtitle ? (
          <p className="text-[#b8c1d1] text-xs md:text-sm mt-1 leading-relaxed break-words">
            {subtitle}
          </p>
        ) : null}
      </div>
      <SampleOpenButton
        href={href}
        viewRoute={viewRoute}
        viewHref={viewHref}
        downloadHref={downloadHref}
        label={subtitle || title}
      />
    </div>
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
      <p className="text-amber-300 text-xs font-bold uppercase tracking-wider mb-2">
        Labeled SAMPLE
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
      <p className="text-[#b8c1d1] text-sm leading-relaxed mb-3 break-words">
        9999 Chapin School Road, Fort Worth, TX 76126 — large-load / DC-adjacent screening with live
        Fort Worth Development Services cites. {PRODUCT_COPY.honestyShort}
      </p>

      <div className="flex flex-col gap-2.5 rounded-xl border border-emerald-500/25 bg-[rgba(15,29,56,0.95)] px-3 py-3 mb-3 md:flex-row md:flex-wrap md:items-center md:gap-x-5 md:gap-y-2">
        <span className="inline-flex items-center gap-2 text-white font-semibold text-sm">
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-emerald-400/60 bg-[#0f1d38] text-emerald-300">
            <Eye className="w-4 h-4" strokeWidth={2.25} />
          </span>
          {PRODUCT_COPY.viewChrome}
        </span>
        <span className="inline-flex items-center gap-2 text-white font-semibold text-sm">
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 text-white">
            <Download className="w-4 h-4" strokeWidth={2.25} />
          </span>
          {PRODUCT_COPY.saveChrome}
        </span>
      </div>

      <div className="space-y-2.5 md:space-y-3">
        {SAMPLE_ROWS.map((row) => (
          <SampleRow key={row.href} {...row} />
        ))}
      </div>
    </div>
  );
}
