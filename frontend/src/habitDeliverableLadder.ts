/**
 * Paid deliverable ladder — Free → Estimator/Permit Runner ($79) → Pro ($149) → IC ($1,500).
 * Premortem rule: more pay = more get; never ungated Pro/IC artifacts on Free/$79.
 */

export const HABIT_TIERS = {
  free: {
    key: 'free' as const,
    name: 'Free Lookups',
    priceLabel: '$0',
  },
  partner: {
    key: 'partner' as const,
    /** Product display name — not “Partner” (affiliate-only word) */
    name: 'Estimator / Permit Runner',
    priceLabel: '$79',
    billing: 'per month',
    oneLiner:
      'Client-site screening habit: full forwardable Bid Risk Receipt, unlocked punch list, Saved Jobs + weekly reminders. Not an estimator CSV desk.',
    features: [
      'Full Bid Risk Receipt PDF — forward to GC / owner / client',
      'Unlocked punch list (owner · due window · Source or Unverified)',
      'Saved Jobs + weekly email reminders for client pipeline',
      'In-app city pack slice for beachhead AHJs',
      'More monthly lookups than Free (habit quota)',
      'Strongest citeable coverage: Dallas / Plano / Austin',
    ] as const,
    notIncluded: [
      'Fee / punch CSV (that is Contractor Pro)',
      'Full city pack PDF / bid packet (Pro)',
      'Deep scout every lookup (Pro)',
      'Counsel DOCX / evidence binder (IC Diligence Bundle)',
    ] as const,
  },
  contractor_pro: {
    key: 'contractor_pro' as const,
    name: 'Contractor Pro',
    priceLabel: '$149',
    billing: 'per month',
    oneLiner:
      'Your bid-week desk: everything in Estimator / Permit Runner, plus deep scout, fee/punch CSV to paste, full city pack PDF, and bid packet.',
    features: [
      'Everything in Estimator / Permit Runner',
      'Deep scout / paid local confirm on every lookup',
      'Fee / punch CSV — trade · owner · due window · source_url (estimator paste)',
      'Full city pack PDF + bid sheet PDF + bid packet',
      'Day-7 re-check habit for live bids',
      'Strongest citeable coverage: Dallas / Plano / Austin',
    ] as const,
    notIncluded: [
      'Counsel DOCX + evidence binder (IC Diligence Bundle)',
      'Parallel-clocks war room as primary (IC)',
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
  return `${labels[artifact]} is a Contractor Pro ($149/mo) deliverable — Estimator / Permit Runner ($79) includes the Bid Risk Receipt + punch + Saved Jobs. Upgrade to paste into your estimate.`;
}
