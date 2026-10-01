/**
 * Shared upgrade stack for sample demos and live results.
 * Every pay button is the same green control. Checklist = what that price includes.
 */
import { Check } from 'lucide-react';
import type { CheckoutLadderTier, LadderUpsell } from '../resultsAccessLadder';

const PAY_BUTTON =
  'w-full px-4 py-2.5 min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold';

export default function TierUpgradeStack({
  rows,
  onCheckout,
  variant = 'cards',
}: {
  rows: LadderUpsell[];
  onCheckout: (tier: CheckoutLadderTier) => void;
  /** cards = summary + checklist + pay button. buttons = identical green CTAs only. */
  variant?: 'cards' | 'buttons';
}) {
  if (!rows.length) return null;

  if (variant === 'buttons') {
    return (
      <div className="flex flex-col gap-2 mt-2 items-stretch">
        {rows.map((row) => (
          <button key={row.tier} type="button" onClick={() => onCheckout(row.tier)} className={PAY_BUTTON}>
            {row.label}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="mt-3 flex flex-col gap-3">
      {rows.map((row, index) => (
        <article
          key={row.tier}
          className="rounded-xl border border-emerald-500/35 bg-slate-950/50 p-3.5 sm:p-4"
        >
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-[11px] font-bold uppercase tracking-wide text-emerald-300/90">
              {index === 0 ? 'Next' : 'Also available'} · {row.name}
            </p>
            <p className="text-sm font-black text-white shrink-0">{row.price}</p>
          </div>
          <p className="text-sm text-gray-100 mt-1.5 leading-relaxed">{row.summary}</p>
          <ul className="mt-2.5 space-y-1.5">
            {row.features.map((feature) => (
              <li key={feature} className="flex items-start gap-2 text-sm text-gray-200">
                <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" aria-hidden />
                <span>{feature}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-amber-100/90 mt-2 leading-relaxed">{row.notThis}</p>
          <button type="button" onClick={() => onCheckout(row.tier)} className={`${PAY_BUTTON} mt-3`}>
            {row.label}
          </button>
        </article>
      ))}
    </div>
  );
}
