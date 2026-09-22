/**
 * Attractive, consistent pitch for the IC Diligence Bundle.
 * Use on Pricing, Checkout, Results, Methodology, Data Center hub.
 */

import { Check, FileSpreadsheet, FileText, Link2, Clock3 } from 'lucide-react';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';

type Variant = 'full' | 'compact' | 'inline';

const FILE_ICONS = [FileText, FileText, FileText, FileSpreadsheet, FileSpreadsheet, Clock3] as const;

export function IcDiligenceBundlePitch({
  variant = 'full',
  className = '',
  showWhy = true,
  showBoundary = true,
}: {
  variant?: Variant;
  className?: string;
  showWhy?: boolean;
  showBoundary?: boolean;
}) {
  if (variant === 'inline') {
    return (
      <div className={`space-y-2 ${className}`}>
        <p className="text-sm text-gray-200 leading-relaxed">{IC_BUNDLE.readyBody}</p>
        <ul className="space-y-1.5">
          {IC_BUNDLE.contents.map((c) => (
            <li key={c.file} className="text-xs text-gray-300 flex gap-2">
              <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
              <span>
                <span className="text-white font-semibold">{c.label}</span>
                {' — '}
                {c.detail}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div
        className={`rounded-xl border border-emerald-500/35 bg-gradient-to-br from-emerald-500/10 via-slate-900/80 to-slate-950/90 p-4 sm:p-5 ${className}`}
      >
        <div className="flex items-start gap-3">
          <FileText className="w-5 h-5 text-emerald-300 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-emerald-100 font-bold text-sm sm:text-base">
              {IC_BUNDLE.productName} · {IC_BUNDLE.priceLabel}
            </p>
            <p className="text-gray-300 text-sm mt-1 leading-relaxed">{IC_BUNDLE.cardDescription}</p>
            <ul className="mt-3 space-y-1.5">
              {IC_BUNDLE.contents.map((c) => (
                <li key={c.file} className="flex gap-2 text-xs sm:text-sm text-gray-200">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>
                    <span className="font-semibold text-white">{c.label}</span>
                    <span className="text-gray-400"> · {c.file}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-2xl border border-emerald-500/40 bg-gradient-to-br from-emerald-600/15 via-slate-900/90 to-slate-950 p-6 sm:p-8 ${className}`}
    >
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/20 border border-emerald-400/40 text-emerald-100 text-xs font-bold uppercase tracking-wide">
          <FileText className="w-3.5 h-3.5" />
          {IC_BUNDLE.badge}
        </span>
        <span className="text-xs font-semibold text-gray-400">{IC_BUNDLE.segment}</span>
      </div>

      <h3 className="text-2xl sm:text-3xl font-black text-white mb-2">
        {IC_BUNDLE.productName}
        <span className="text-emerald-300"> — {IC_BUNDLE.priceLabel}</span>
      </h3>
      <p className="text-gray-300 text-base sm:text-lg leading-relaxed mb-4">{IC_BUNDLE.oneLiner}</p>

      {showWhy ? (
        <p className="text-emerald-100/90 text-sm sm:text-base leading-relaxed mb-6 border-l-2 border-emerald-400/50 pl-4">
          {IC_BUNDLE.whyBuy}
        </p>
      ) : null}

      <p className="text-xs font-bold uppercase tracking-wider text-emerald-300/90 mb-3">
        What’s in the ZIP
      </p>
      <div className="grid sm:grid-cols-1 gap-3 mb-6">
        {IC_BUNDLE.contents.map((c, i) => {
          const Icon = FILE_ICONS[i] || Link2;
          return (
            <div
              key={c.file}
              className="flex gap-3 rounded-xl border border-white/10 bg-slate-950/50 p-3.5"
            >
              <div className="w-9 h-9 rounded-lg bg-emerald-500/15 border border-emerald-400/30 flex items-center justify-center shrink-0">
                <Icon className="w-4 h-4 text-emerald-300" />
              </div>
              <div className="min-w-0">
                <p className="text-white font-bold text-sm">{c.label}</p>
                <p className="text-[11px] font-mono text-emerald-300/80 mt-0.5">{c.file}</p>
                <p className="text-gray-400 text-sm mt-1 leading-relaxed">{c.detail}</p>
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-sm text-gray-400 mb-2">{IC_BUNDLE.forWhom}</p>
      {showBoundary ? (
        <p className="text-xs text-amber-200/85 leading-relaxed">{IC_BUNDLE.notThis}</p>
      ) : null}
    </div>
  );
}
