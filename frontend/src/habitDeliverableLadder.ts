/**
 * Paid deliverable ladder — Free → Estimator/Permit Runner ($79) → Pro ($149) → IC ($1,500).
 * Premortem rule: more pay = more get; never ungated Pro/IC artifacts on Free/$79.
 * Keep in lockstep with PricingPage + IC_BUNDLE + sample tier ladder.
 */

export const HABIT_TIERS = {
  free: {
    key: 'free' as const,
    name: 'Free Lookups',
    priceLabel: '$0',
    billing: 'Free lead magnet',
    oneLiner:
      'First look before you burn a bid day — bid-or-walk preview, Source or Unverified. No card.',
    features: [
      'Bid-or-walk preview for one US address — no card',
      'Top punch-list risks (soft-locked — top 5 lines)',
      'Source or Unverified on every visible line',
      'Forward Bid Risk Receipt to unlock a bit more (still less than Estimator)',
      'Text or email your results',
    ] as const,
    notIncluded: [
      'Full Bid Risk Receipt PDF habit desk (Estimator / Permit Runner)',
      'Fee / punch CSV + city pack (Contractor Pro)',
      'IC Diligence Bundle ZIP (memo + boardroom + DOCX + Excel)',
    ] as const,
  },
  partner: {
    key: 'partner' as const,
    /** Product display name — not “Partner” (affiliate-only word) */
    name: 'Estimator / Permit Runner',
    priceLabel: '$79',
    billing: 'per month',
    oneLiner:
      'Stop losing the thread with the GC — full forwardable Receipt + unlocked punch + Saved Jobs for client sites.',
    features: [
      'Full Bid Risk Receipt PDF — forward to GC / owner / client',
      'Unlocked punch list (owner · due window · Source or Unverified)',
      'Saved Jobs + weekly email reminders for client pipeline',
      'In-app city pack slice for beachhead AHJs',
      'More monthly lookups than Free (habit quota)',
      'Strongest citeable coverage: Dallas / Plano / Austin / Fort Worth',
    ] as const,
    notIncluded: [
      'Fee / punch CSV (that is Contractor Pro)',
      'Full city pack PDF / bid packet (Pro)',
      'Deep scout every lookup (Pro)',
      'Counsel DOCX / Excel workbooks / IC Diligence Bundle ZIP',
    ] as const,
  },
  contractor_pro: {
    key: 'contractor_pro' as const,
    name: 'Contractor Pro',
    priceLabel: '$149',
    billing: 'per month',
    oneLiner:
      'Bid-week desk if you own the number — City Pack, fee CSV, bid packet. One missed fee line pays for the month.',
    features: [
      'Everything in Estimator / Permit Runner',
      'Paid local confirm / light scout on every lookup',
      'Fee / punch CSV — trade · owner · due window · source_url (estimator paste)',
      'Full City Pack PDF + bid sheet PDF + bid packet',
      'Day-7 re-check habit for live bids',
      'Strongest citeable coverage: Dallas / Plano / Austin / Fort Worth',
    ] as const,
    notIncluded: [
      'Counsel DOCX + evidence binder Excel (IC Diligence Bundle)',
      'Boardroom PDF + parallel-clocks war room as primary (IC)',
      'Estimator Excel workbooks — Fees · Punch · Evidence (IC)',
    ] as const,
  },
} as const;

/** Artifacts that require Contractor Pro or IC entitlement */
export const PRO_DESK_ARTIFACTS = [
  'bid_sheet_csv',
  'bid_sheet_pdf',
  'city_pack_pdf',
  'bid_packet_pdf',
] as const;

export type ProDeskArtifact = (typeof PRO_DESK_ARTIFACTS)[number];

export function proDeskGateMessage(artifact: ProDeskArtifact): string {
  const labels: Record<ProDeskArtifact, string> = {
    bid_sheet_csv: 'Fee / punch CSV',
    bid_sheet_pdf: 'Bid sheet PDF',
    city_pack_pdf: 'Full city pack PDF',
    bid_packet_pdf: 'Full bid packet',
  };
  return `${labels[artifact]} is on the Contractor Pro bid desk ($149/mo) — Estimator ($79) is the Receipt you forward. Upgrade when you need fee dollars and City Pack on the estimate.`;
}
