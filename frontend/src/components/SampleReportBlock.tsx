/**
 * Sample tier downloads — Fort Worth Chapin DC-adjacent site at every tier.
 * Eye = view in app. Download icon = save to disk.
 * Icon columns align evenly down the list.
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
    subtitle: 'Overview of Free / Partner / Pro / IC on one site',
    tier: null as string | null,
    price: null as string | null,
    highlight: true,
  },
  {
    href: '/sample/free-preview.pdf',
    title: HABIT_TIERS.free.name,
    subtitle: HABIT_TIERS.free.oneLiner,
    tier: HABIT_TIERS.free.name,
    price: HABIT_TIERS.free.priceLabel,
    highlight: false,
  },
  {
    href: '/sample/partner-receipt.pdf',
    title: HABIT_TIERS.partner.name,
    subtitle: HABIT_TIERS.partner.oneLiner,
    tier: HABIT_TIERS.partner.name,
    price: `${HABIT_TIERS.partner.priceLabel}/mo`,
    highlight: false,
  },
  {
    href: '/sample/pro-desk.zip',
    title: HABIT_TIERS.contractor_pro.name,
    subtitle: HABIT_TIERS.contractor_pro.oneLiner,
    tier: HABIT_TIERS.contractor_pro.name,
    price: `${HABIT_TIERS.contractor_pro.priceLabel}/mo`,
    highlight: false,
  },
  {
    href: '/sample/ic-diligence-bundle.zip',
    title: IC_BUNDLE.tierName,
    subtitle: IC_BUNDLE.cardDescription,
    tier: IC_BUNDLE.tierName,
    price: IC_BUNDLE.priceLabel,
    highlight: false,
  },
] as const;

/** @deprecated — use SAMPLE_ROWS */
export const SAMPLE_DOWNLOADS = SAMPLE_ROWS.filter((r) => !r.highlight).map((r) => ({
  tier: r.tier || r.title,
  price: r.price || '',
  href: r.href,
  shortLabel: r.title,
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
      {/* Fixed track: [eye][gap][download] — same width on every row */}
      <div
        className="grid grid-cols-2 gap-2 w-[6.25rem]"
        role="group"
        aria-label={`${title}: view or download`}
      >
        <button
          type="button"
          title={`View ${title}`}
          aria-label={`View ${title}`}
          onClick={(e) => void run('view', e)}
          disabled={busy !== null}
          className={`${iconBtn} border border-emerald-400/50 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-100`}
        >
          {busy === 'view' ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Eye className="w-5 h-5" />
          )}
        </button>
        <button
          type="button"
          title={`Download ${title}`}
          aria-label={`Download ${title}`}
          onClick={(e) => void run('download', e)}
          disabled={busy !== null}
          className={`${iconBtn} border border-white/20 bg-white/5 hover:bg-white/10 text-white`}
        >
          {busy === 'download' ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Download className="w-5 h-5" />
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
      className={`grid grid-cols-[1fr_auto] items-center gap-3 rounded-xl border ${
        highlight
          ? 'border-emerald-500/30 bg-emerald-500/10'
          : 'border-white/10 bg-slate-950/50'
      } ${compact ? 'p-3.5' : 'p-4 sm:p-5'}`}
    >
      <div className="min-w-0 pr-2">
        <p className={`text-white font-bold truncate ${compact ? 'text-sm' : 'text-sm sm:text-base'}`}>
          {title}
          {price ? (
            <>
              {' '}
              <span className="text-emerald-300 font-semibold">· {price}</span>
            </>
          ) : null}
        </p>
        {!compact && subtitle ? (
          <p className="text-gray-400 text-sm mt-1 leading-relaxed line-clamp-2">{subtitle}</p>
        ) : null}
      </div>
      <SampleOpenButton href={href} label={title} />
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
      <p className="text-amber-200/90 text-xs font-bold uppercase tracking-wider mb-2">
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
      <p className={`text-gray-300 leading-relaxed ${compact ? 'text-sm mb-1' : 'text-lg mb-2'}`}>
        9999 Chapin School Road, Fort Worth, TX 76126 — large-load / data-center-adjacent
        screening with live Fort Worth Development Services cites.
      </p>
      <p className={`text-gray-400 ${compact ? 'text-xs mb-4' : 'text-sm mb-6'}`}>
        Planning aid only — not a quote, sealed bid, interconnection study, or AHJ filing.{' '}
        <span className="text-gray-300">
          Eye = view in Reg Guard. Download = save to your device.
        </span>
      </p>

      <div className={compact ? 'space-y-2.5' : 'space-y-3'}>
        {SAMPLE_ROWS.map((row) => (
          <SampleRow
            key={row.href}
            href={row.href}
            title={row.highlight ? row.title : row.tier || row.title}
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
