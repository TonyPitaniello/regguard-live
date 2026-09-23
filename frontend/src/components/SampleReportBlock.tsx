/**
 * Sample tier downloads — Fort Worth Chapin DC-adjacent site at every tier.
 * Used on home (after intro) and /sample-report.
 *
 * Files are served from frontend/public/sample/ (same-origin) so downloads
 * work even when the Render API is behind on deploys.
 * Clicks open the in-app viewer and download in the same action.
 */

import { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { HABIT_TIERS } from '../habitDeliverableLadder';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';
import { openAndDownloadUrl } from '../openAndDownload';

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

export const SAMPLE_DOWNLOADS = [
  {
    tier: HABIT_TIERS.free.name,
    price: HABIT_TIERS.free.priceLabel,
    href: '/sample/free-preview.pdf',
    label: 'Sample Free Preview PDF',
    detail: HABIT_TIERS.free.oneLiner,
  },
  {
    tier: HABIT_TIERS.partner.name,
    price: `${HABIT_TIERS.partner.priceLabel}/mo`,
    href: '/sample/partner-receipt.pdf',
    label: 'Sample Full Bid Risk Receipt PDF',
    detail: HABIT_TIERS.partner.oneLiner,
  },
  {
    tier: HABIT_TIERS.contractor_pro.name,
    price: `${HABIT_TIERS.contractor_pro.priceLabel}/mo`,
    href: '/sample/pro-desk.zip',
    label: 'Sample Pro Desk ZIP',
    detail: HABIT_TIERS.contractor_pro.oneLiner,
  },
  {
    tier: IC_BUNDLE.tierName,
    price: IC_BUNDLE.priceLabel,
    href: '/sample/ic-diligence-bundle.zip',
    label: 'Sample IC Diligence Bundle ZIP',
    detail: IC_BUNDLE.cardDescription,
  },
] as const;

export export function SampleOpenButton({
  href,
  label,
  className,
}: {
  href: string;
  label: string;
  className: string;
}) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const onClick = async () => {
    setBusy(true);
    setErr('');
    try {
      await openAndDownloadUrl(sampleUrl(href), sampleFilename(href));
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Open / download failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="shrink-0">
      <button type="button" onClick={() => void onClick()} disabled={busy} className={className}>
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
        {busy ? 'Opening…' : label}
      </button>
      {err ? <p className="text-amber-200 text-xs mt-1">{err}</p> : null}
    </div>
  );
}

export function SampleReportBlock({
  compact = false,
  id = 'sample-report',
}: {
  /** Tighter layout for home (between intro and address form) */
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
      <p className={`text-gray-400 ${compact ? 'text-xs mb-4' : 'text-sm mb-8'}`}>
        Planning aid only — not a quote, sealed bid, interconnection study, or AHJ filing. Opens in
        Reg Guard and downloads to your device.
      </p>

      <SampleOpenButton
        href="/sample/tier-ladder.pdf"
        label="Download Sample Tier Ladder PDF"
        className={`inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition min-h-[44px] disabled:opacity-60 ${
          compact ? 'px-4 py-2.5 text-sm mb-4' : 'px-6 py-3 mb-10'
        }`}
      />

      <div className={compact ? 'space-y-2.5' : 'space-y-4'}>
        {SAMPLE_DOWNLOADS.map((s) => (
          <div
            key={s.href}
            className={`rounded-xl border border-white/10 bg-slate-950/50 flex flex-col sm:flex-row sm:items-center gap-3 ${
              compact ? 'p-3.5' : 'p-5 gap-4'
            }`}
          >
            <div className="min-w-0 flex-1">
              <p className={`text-white font-bold ${compact ? 'text-sm' : ''}`}>
                {s.tier}{' '}
                <span className="text-emerald-300 font-semibold">· {s.price}</span>
              </p>
              {!compact ? (
                <p className="text-gray-400 text-sm mt-1 leading-relaxed">{s.detail}</p>
              ) : null}
            </div>
            <SampleOpenButton
              href={s.href}
              label={s.label}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 border border-emerald-400/40 hover:bg-emerald-500/15 text-emerald-100 font-semibold rounded-lg transition min-h-[44px] shrink-0 text-sm disabled:opacity-60"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
