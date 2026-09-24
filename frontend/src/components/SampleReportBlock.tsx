/**
 * Sample tier downloads — Fort Worth Chapin DC-adjacent site at every tier.
 * Eye = view in app. Download icon = save to disk.
 * Icon columns align evenly; copy + colors match the Reg Guard palette.
 */

import { useState, type MouseEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Eye, Loader2 } from 'lucide-react';
import { HABIT_TIERS } from '../habitDeliverableLadder';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';
import { downloadOnlyUrl, viewInAppUrl } from '../openAndDownload';

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
    'pro-desk.zip': 'RegGuard_Sample_Pro_Desk.zip',
    'ic-diligence-bundle.zip': 'RegGuard_Sample_IC_Diligence_Bundle.zip',
    'plano-punch-list.pdf': 'RegGuard_Sample_Estimator_Receipt.pdf',
  };
  return map[base] || `RegGuard_Sample_${base}`;
}

/** All sample rows — same layout so eye / download columns line up */
export const SAMPLE_ROWS = [
  {
    href: '/sample/tier-ladder.pdf',
    title: 'Sample Tier Ladder PDF',
    subtitle: 'What Free, Estimator / Permit Runner, Pro, and IC include on this site',
    price: null as string | null,
    highlight: true,
  },
  {
    href: '/sample/free-preview.pdf',
    title: HABIT_TIERS.free.name,
    subtitle: 'Sample Free Preview PDF',
    price: HABIT_TIERS.free.priceLabel,
    highlight: false,
  },
  {
    href: '/sample/partner-receipt.pdf',
    title: HABIT_TIERS.partner.name,
    subtitle: 'Sample Full Bid Risk Receipt PDF',
    price: `${HABIT_TIERS.partner.priceLabel}/mo`,
    highlight: false,
  },
  {
    href: '/sample/pro-desk.zip',
    title: HABIT_TIERS.contractor_pro.name,
    subtitle: 'Sample Pro Desk ZIP',
    price: `${HABIT_TIERS.contractor_pro.priceLabel}/mo`,
    highlight: false,
  },
  {
    href: '/sample/ic-diligence-bundle.zip',
    title: IC_BUNDLE.tierName,
    subtitle: 'Sample IC Diligence Bundle ZIP',
    price: IC_BUNDLE.priceLabel,
    highlight: false,
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

const iconBtn =
  'inline-flex items-center justify-center h-11 w-11 rounded-lg transition disabled:opacity-60 shrink-0';

/** Fixed-width eye + download pair so every row aligns. */
export function SampleOpenButton({
  href,
  label,
  className,
}: {
  href: string;
  label?: string;
  className?: string;
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState<'view' | 'download' | null>(null);
  const [err, setErr] = useState('');
  const title = label || sampleFilename(href).replace(/^RegGuard_/, '').replace(/_/g, ' ');

  const run = async (mode: 'view' | 'download', e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setBusy(mode);
    setErr('');
    try {
      const url = sampleUrl(href);
      const name = sampleFilename(href);
      if (mode === 'view') {
        await viewInAppUrl(url, name, { navigate: (to) => navigate(to) });
      } else {
        await downloadOnlyUrl(url, name);
      }
    } catch (errObj) {
      setErr(errObj instanceof Error ? errObj.message : 'Action failed');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className={`shrink-0 ${className || ''}`}>
      <div
        className="grid grid-cols-2 gap-2 w-[6.25rem]"
        role="group"
        aria-label={`${title}: view or download`}
      >
        <button
          type="button"
          title={`View ${title} in Reg Guard`}
          aria-label={`View ${title} in Reg Guard`}
          onClick={(e) => void run('view', e)}
          disabled={busy !== null}
          className={`${iconBtn} border border-emerald-400/60 bg-[#0f1d38] hover:bg-emerald-500/20 text-emerald-300`}
        >
          {busy === 'view' ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Eye className="w-5 h-5" strokeWidth={2.25} />
          )}
        </button>
        <button
          type="button"
          title={`Download ${title}`}
          aria-label={`Download ${title}`}
          onClick={(e) => void run('download', e)}
          disabled={busy !== null}
          className={`${iconBtn} bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white border border-emerald-400/30 shadow-md shadow-green-500/20`}
        >
          {busy === 'download' ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Download className="w-5 h-5" strokeWidth={2.25} />
          )}
        </button>
      </div>
      {err ? <p className="text-amber-200 text-xs mt-1 max-w-[6.25rem] text-center">{err}</p> : null}
    </div>
  );
}

function SampleRow({
  href,
  title,
  subtitle,
  price,
  highlight,
  compact,
}: {
  href: string;
  title: string;
  subtitle: string;
  price: string | null;
  highlight?: boolean;
  compact?: boolean;
}) {
  return (
    <div
      className={`grid grid-cols-[minmax(0,1fr)_6.25rem] items-center gap-3 rounded-xl border ${
        highlight
          ? 'border-emerald-500/35 bg-emerald-500/10'
          : 'border-[rgba(61,79,143,0.4)] bg-[rgba(10,20,41,0.85)]'
      } ${compact ? 'p-3.5' : 'p-4 sm:p-5'}`}
    >
      <div className="min-w-0">
        <p className={`text-white font-bold leading-snug ${compact ? 'text-sm' : 'text-sm sm:text-base'}`}>
          {title}
          {price ? (
            <>
              {' '}
              <span className="text-emerald-300 font-semibold whitespace-nowrap">· {price}</span>
            </>
          ) : null}
        </p>
        {subtitle ? (
          <p className={`text-[#b8c1d1] mt-1 leading-relaxed ${compact ? 'text-xs' : 'text-sm'}`}>
            {subtitle}
          </p>
        ) : null}
      </div>
      <SampleOpenButton href={href} label={subtitle || title} />
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
    <div id={id} className={compact ? 'text-left' : ''}>
      <p className="text-amber-300 text-xs font-bold uppercase tracking-wider mb-2">
        Labeled SAMPLE
      </p>
      <h3
        className={
          compact
            ? 'text-xl sm:text-2xl font-black text-white mb-2'
            : 'text-4xl sm:text-5xl font-black text-white mb-4'
        }
      >
        Same site. Every tier.
      </h3>
      <p className={`text-[#b8c1d1] leading-relaxed ${compact ? 'text-sm mb-3' : 'text-base mb-4'}`}>
        9999 Chapin School Road, Fort Worth, TX 76126 — large-load / data-center-adjacent
        screening with live Fort Worth Development Services cites. Planning aid only — not a quote,
        sealed bid, or AHJ filing.
      </p>

      {/* Legend matches the two real buttons */}
      <div
        className={`flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border border-emerald-500/25 bg-[rgba(15,29,56,0.95)] ${
          compact ? 'px-3 py-2.5 mb-3 text-xs' : 'px-4 py-3 mb-4 text-sm'
        }`}
      >
        <span className="inline-flex items-center gap-2 text-white font-semibold">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-emerald-400/60 bg-[#0f1d38] text-emerald-300">
            <Eye className="w-4 h-4" strokeWidth={2.25} />
          </span>
          View in Reg Guard
        </span>
        <span className="inline-flex items-center gap-2 text-white font-semibold">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 text-white">
            <Download className="w-4 h-4" strokeWidth={2.25} />
          </span>
          Download to your device
        </span>
      </div>

      <div className={`grid grid-cols-[minmax(0,1fr)_6.25rem] gap-3 px-1 mb-2 ${compact ? '' : ''}`}>
        <p className="text-[10px] font-bold uppercase tracking-wider text-[#b8c1d1]">Sample</p>
        <div className="grid grid-cols-2 gap-2 text-center text-[10px] font-bold uppercase tracking-wider text-emerald-300">
          <span>View</span>
          <span>Save</span>
        </div>
      </div>

      <div className={compact ? 'space-y-2.5' : 'space-y-3'}>
        {SAMPLE_ROWS.map((row) => (
          <SampleRow
            key={row.href}
            href={row.href}
            title={row.title}
            subtitle={row.subtitle}
            price={row.price}
            highlight={row.highlight}
            compact={compact}
          />
        ))}
      </div>
    </div>
  );
}
