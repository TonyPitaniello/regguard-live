/**
 * Sample Report — same Fort Worth DC-adjacent site at every paid tier.
 * Downloads use production generators labeled SAMPLE.
 */

import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Download } from 'lucide-react';
import { backendUrl } from '../env';
import { HABIT_TIERS } from '../habitDeliverableLadder';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';

const SAMPLES = [
  {
    tier: HABIT_TIERS.free.name,
    price: HABIT_TIERS.free.priceLabel,
    href: '/sample/free-preview.pdf',
    label: 'Free preview PDF',
    detail: HABIT_TIERS.free.oneLiner,
  },
  {
    tier: HABIT_TIERS.partner.name,
    price: `${HABIT_TIERS.partner.priceLabel}/mo`,
    href: '/sample/partner-receipt.pdf',
    label: 'Full Bid Risk Receipt PDF',
    detail: HABIT_TIERS.partner.oneLiner,
  },
  {
    tier: HABIT_TIERS.contractor_pro.name,
    price: `${HABIT_TIERS.contractor_pro.priceLabel}/mo`,
    href: '/sample/pro-desk.zip',
    label: 'Pro desk ZIP (Receipt + CSV + city pack)',
    detail: HABIT_TIERS.contractor_pro.oneLiner,
  },
  {
    tier: IC_BUNDLE.tierName,
    price: IC_BUNDLE.priceLabel,
    href: '/sample/ic-diligence-bundle.zip',
    label: 'IC Diligence Bundle ZIP',
    detail: IC_BUNDLE.cardDescription,
  },
] as const;

export default function SampleReportPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between gap-4">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <button
            type="button"
            onClick={() => navigate('/pricing')}
            className="text-sm font-semibold text-emerald-300 hover:text-white transition"
          >
            Pricing
          </button>
        </div>
      </header>

      <section className="px-4 py-14 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <p className="text-amber-200/90 text-xs font-bold uppercase tracking-wider mb-3">
            Labeled SAMPLE
          </p>
          <h1 className="text-4xl sm:text-5xl font-black text-white mb-4">
            Same site. Every tier.
          </h1>
          <p className="text-lg text-gray-300 mb-2">
            9999 Chapin School Road, Fort Worth, TX 76126 — large-load / data-center-adjacent
            screening with live Fort Worth Development Services cites.
          </p>
          <p className="text-sm text-gray-400 mb-8">
            Planning aid only — not a quote, sealed bid, interconnection study, or AHJ filing.
            Payments via Stripe; Reg Guard does not store cards.
          </p>

          <a
            href={backendUrl('/sample/tier-ladder.pdf')}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition min-h-[44px] mb-10"
          >
            <Download className="w-4 h-4" />
            Download tier ladder PDF (overview)
          </a>

          <div className="space-y-4">
            {SAMPLES.map((s) => (
              <div
                key={s.href}
                className="rounded-xl border border-white/10 bg-slate-950/50 p-5 flex flex-col sm:flex-row sm:items-center gap-4"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-white font-bold">
                    {s.tier}{' '}
                    <span className="text-emerald-300 font-semibold">· {s.price}</span>
                  </p>
                  <p className="text-gray-400 text-sm mt-1 leading-relaxed">{s.detail}</p>
                </div>
                <a
                  href={backendUrl(s.href)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center justify-center gap-2 px-4 py-2.5 border border-emerald-400/40 hover:bg-emerald-500/15 text-emerald-100 font-semibold rounded-lg transition min-h-[44px] shrink-0"
                >
                  <Download className="w-4 h-4" />
                  {s.label}
                </a>
              </div>
            ))}
          </div>

          <div className="mt-10 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5">
            <p className="text-emerald-100 font-bold mb-2">{IC_BUNDLE.productName} ZIP contains</p>
            <ul className="space-y-1.5 text-sm text-gray-300">
              {IC_BUNDLE.contents.map((c) => (
                <li key={c.file}>
                  <span className="text-white font-semibold">{c.label}</span>
                  <span className="text-gray-500"> · {c.file}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
