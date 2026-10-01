/**
 * Free → Estimator → Pro → IC → IC Annual access ladder for Site Diligence Results.
 * Used by sample demos and live entitlement gating on every new scan.
 *
 * VALUE RULE (premortem): more pay ⇒ strictly more visible content + artifacts.
 * Never let Free (even after share unlock) show ≥ Estimator punch/findings.
 *
 * Visibility matrix (canonical):
 *   Free soft-lock:     5 punch · 3 findings · contingency blurred · fee $ blurred · no Pro desk
 *   Free after share:   6 punch · 4 findings · contingency % on · fee $ still blurred · no Pro desk
 *   Estimator ($79):    full punch · full habit findings · contingency % on · fee $ blurred · no Pro desk
 *   Pro ($149):         full punch · full findings · fee $ on · City Pack PDF/CSV/bid packet
 *   IC ($1,500):        Pro desk + counsel ZIP (memo · boardroom · DOCX · Excel)
 *
 * Upsell: each level lists every higher SKU — next step first (primary), then up to highest cost.
 *
 * HARD RULE: display tier comes from THIS run's research_depth / demoTier.
 * Sticky entitlements must NEVER invent Pro/IC on a free or missing-depth run.
 * Downloads unlock only for what this tier has paid for (see downloadsAllowedForTier).
 */

import { TIER_VOICE, nextVoiceForLadderTier } from './tierVoice';

export type ResultsLadderTier = 'free' | 'partner' | 'pro' | 'ic';

export type CheckoutLadderTier = 'partner' | 'contractor_pro' | 'ic_project' | 'ic_annual';

export type ResultsLadder = {
  tier: ResultsLadderTier;
  /** Free soft-lock: limited punch + blurred contingency until share/upgrade */
  softLocked: boolean;
  punchVisible: number;
  findingsVisible: number;
  ownsPartner: boolean;
  ownsPro: boolean;
  ownsIc: boolean;
  ownsIcAnnual: boolean;
  allowProDesk: boolean;
  /** Blur Pro desk dollars / CSV / city pack PDF chrome */
  blurProDesk: boolean;
  /**
   * Trailing punch lines shown as Pro-desk teasers.
   * Only for Free (never for Estimator — they already paid for unlocked punch).
   */
  proBlurPunchTeasers: number;
  /** How many synthetic locked punch rows to paint when the list is short (sample theater) */
  syntheticBlurTeasers: number;
};

export type LadderUpsell = {
  tier: CheckoutLadderTier;
  label: string;
  /** Short “what you get” line */
  offers?: string;
  name: string;
  price: string;
  /** One compelling, accurate sentence */
  summary: string;
  /** What this level includes — buyer language, not a SKU dump */
  features: readonly string[];
  /** Honest boundary so the next level stays distinct */
  notThis: string;
  primary?: boolean;
};

const UPSELL_PACK: Record<
  CheckoutLadderTier,
  Pick<LadderUpsell, 'name' | 'price' | 'summary' | 'features' | 'notThis' | 'label' | 'offers'>
> = {
  partner: {
    name: 'Estimator / Permit Runner',
    price: '$79/mo',
    summary:
      'The Receipt the GC can actually file — full punch, Saved Jobs, and a stamp you can forward every client site.',
    features: [
      'Full Bid Risk Receipt PDF — forward to GC, owner, or client',
      'Unlocked punch list (owner, due window, Source or Unverified)',
      'Saved Jobs and reminders so the site doesn’t vanish in the thread',
      'More monthly lookups than Free',
    ],
    notThis: 'Not included: Full City Pack PDF, fee/punch CSV, bid packet, or counsel ZIP.',
    label: TIER_VOICE.free.upsellCta,
    offers: TIER_VOICE.free.upsellOffers,
  },
  contractor_pro: {
    name: 'Contractor Pro',
    price: '$149/mo',
    summary:
      'The bid desk when your number has to hold — fee dollars, Full City Pack PDF, CSV, and bid packet beside the Receipt.',
    features: [
      'Everything in Estimator / Permit Runner',
      'Full City Pack PDF — fees, gotchas, AHJ links',
      'Fee/punch CSV, bid sheet, and bid packet',
      'Paid local confirm on lookups (planning aid — confirm the live schedule)',
    ],
    notThis: 'Not included: counsel ZIP (memo, boardroom, Word, Excel). City Pack is not that package.',
    label: TIER_VOICE.partner.upsellCta,
    offers: TIER_VOICE.partner.upsellOffers,
  },
  ic_project: {
    name: 'IC Diligence Bundle',
    price: '$1,500',
    summary:
      'The ZIP counsel and lenders open for one capital site — memo, boardroom, editable Word with exhibits, Excel evidence. Not a bigger City Pack.',
    features: [
      'Decision memo — HOLD or CLEAR you can forward',
      'Boardroom PDF plus editable counsel Word with exhibits',
      'Excel: Fees, Punch, Evidence, and an evidence index',
      'One bound address. A different site is a new purchase.',
    ],
    notThis: 'Not a quote, sealed bid, interconnection study, geotech report, or AHJ filing.',
    label: TIER_VOICE.pro.upsellCta,
    offers: TIER_VOICE.pro.upsellOffers,
  },
  ic_annual: {
    name: 'IC Annual',
    price: '$15,000/yr',
    summary:
      'Same counsel ZIP for more capital sites on this purchase email — ahead of $1,500 per site once you pass about ~10.',
    features: [
      'Diligence Bundle ZIP for each new bound capital site on this email',
      'Memo, boardroom, Word, and Excel — same shape, new address',
      'Ahead of Project rate past about ~10 sites in a year',
      'Built for IC, owner’s rep, sponsor, and lender packages',
    ],
    notThis:
      'Not day-to-day Contractor Pro. A different purchase email still needs its own $1,500 Project.',
    label: TIER_VOICE.ic.upsellCta,
    offers: TIER_VOICE.ic.upsellOffers,
  },
};

function pushUpsell(rows: LadderUpsell[], tier: CheckoutLadderTier, primary: boolean) {
  const pack = UPSELL_PACK[tier];
  rows.push({ tier, primary, ...pack });
}

/** Soft-locked Free — matches HABIT_TIERS.free “top ~5” */
export const FREE_SOFT_PUNCH = 5;
/** Free after share unlock — must stay strictly below Estimator */
export const FREE_UNLOCKED_PUNCH = 6;
/** Estimator paid for unlocked punch — full list */
export const PARTNER_PUNCH = 99;
export const PRO_PUNCH = 99;

export const FREE_SOFT_FINDINGS = 3;
export const FREE_UNLOCKED_FINDINGS = 4;
export const PARTNER_FINDINGS = 12;
export const PRO_FINDINGS = 99;

/** Always show ≥ this many locked blur rows on Free soft-lock (sample parity) */
export const FREE_SYNTHETIC_BLUR_TEASERS = 3;

export function normalizeAccessTier(raw?: string | null): ResultsLadderTier | null {
  const t = String(raw || '')
    .toLowerCase()
    .trim();
  if (!t) return null;
  if (t === 'free') return 'free';
  if (t === 'partner' || t === 'estimator') return 'partner';
  if (t === 'pro' || t === 'contractor_pro') return 'pro';
  if (t === 'ic' || t === 'ic_project' || t === 'ic_consultant' || t === 'ic_annual' || t === 'sponsor')
    return 'ic';
  return null;
}

/**
 * True when this analysis was a Free FinOps / instant preview run — UI must blur like Free.
 * Explicit partner/pro/ic depth always wins over a leftover preview flag.
 */
export function isFreeResearchDepth(depth?: string | null, preview?: boolean): boolean {
  const d = String(depth || '')
    .toLowerCase()
    .trim();
  if (
    d === 'partner' ||
    d === 'estimator' ||
    d === 'pro' ||
    d === 'pro_partial' ||
    d === 'pro_light' ||
    d === 'pro_local' ||
    d.startsWith('pro_') ||
    d === 'ic' ||
    d === 'ic_full'
  ) {
    return false;
  }
  if (d === 'free' || d === 'instant' || d === 'preview') return true;
  // Missing depth: preview flag or empty → Free soft-lock (never invent Pro)
  if (preview === true) return true;
  return !d;
}

/**
 * Map research_depth → ladder tier for hard caps.
 * Live UI must match sample demos: depth cannot be unlocked by sticky higher entitlements.
 * Empty / unknown depth hard-caps to Free.
 */
export function ladderTierFromResearchDepth(
  depth?: string | null,
  preview?: boolean
): ResultsLadderTier {
  if (isFreeResearchDepth(depth, preview)) return 'free';
  const d = String(depth || '')
    .toLowerCase()
    .trim();
  if (d === 'partner' || d === 'estimator') return 'partner';
  if (
    d === 'pro' ||
    d === 'pro_partial' ||
    d === 'pro_light' ||
    d === 'pro_local' ||
    d.startsWith('pro_')
  ) {
    return 'pro';
  }
  if (d === 'ic' || d === 'ic_full') return 'ic';
  return 'free';
}

/** Highest entitlement wins — used when stamping live scan results. */
export function accessTierFromEntitlements(tiers: string[] | undefined | null): ResultsLadderTier {
  const owned = new Set((tiers || []).map((t) => String(t || '').toLowerCase()).filter(Boolean));
  if (['ic_project', 'ic_consultant', 'ic_annual', 'sponsor'].some((t) => owned.has(t))) return 'ic';
  if (owned.has('contractor_pro')) return 'pro';
  if (owned.has('partner')) return 'partner';
  return 'free';
}

/**
 * Higher-tier checkout CTAs — next step first, then every step up to highest cost.
 * Free → Estimator → Pro → IC Project → IC Annual
 */
export function ladderUpsells(
  tier: ResultsLadderTier,
  opts?: { ownsIcAnnual?: boolean; nextOnly?: boolean }
): LadderUpsell[] {
  const nextOnly = opts?.nextOnly === true;
  const rows: LadderUpsell[] = [];

  if (tier === 'free') {
    pushUpsell(rows, 'partner', true);
    if (!nextOnly) {
      pushUpsell(rows, 'contractor_pro', false);
      pushUpsell(rows, 'ic_project', false);
      if (!opts?.ownsIcAnnual) pushUpsell(rows, 'ic_annual', false);
    }
    return rows;
  }
  if (tier === 'partner') {
    pushUpsell(rows, 'contractor_pro', true);
    if (!nextOnly) {
      pushUpsell(rows, 'ic_project', false);
      if (!opts?.ownsIcAnnual) pushUpsell(rows, 'ic_annual', false);
    }
    return rows;
  }
  if (tier === 'pro') {
    pushUpsell(rows, 'ic_project', true);
    if (!nextOnly && !opts?.ownsIcAnnual) pushUpsell(rows, 'ic_annual', false);
    return rows;
  }
  if (opts?.ownsIcAnnual) {
    const next = nextVoiceForLadderTier('ic', { ownsIcAnnual: true });
    const pack = UPSELL_PACK.ic_project;
    rows.push({
      ...pack,
      tier: 'ic_project',
      label: next.upsellCta,
      offers: next.upsellOffers,
      primary: true,
    });
    return rows;
  }
  pushUpsell(rows, 'ic_annual', true);
  return rows;
}

/** Which bid-time downloads this ladder tier has paid for (display + gate). */
export function downloadsAllowedForTier(tier: ResultsLadderTier): {
  receiptPreview: boolean;
  receiptHabit: boolean;
  proDesk: boolean;
  icBundle: boolean;
} {
  if (tier === 'ic') {
    return { receiptPreview: true, receiptHabit: true, proDesk: true, icBundle: true };
  }
  if (tier === 'pro') {
    return { receiptPreview: true, receiptHabit: true, proDesk: true, icBundle: false };
  }
  if (tier === 'partner') {
    return { receiptPreview: true, receiptHabit: true, proDesk: false, icBundle: false };
  }
  // free
  return { receiptPreview: true, receiptHabit: false, proDesk: false, icBundle: false };
}

export function resolveResultsLadder(input: {
  demoTier?: 'free' | 'partner' | 'pro' | null;
  entitlementTiers?: string[];
  accessTier?: string | null;
  isDeep?: boolean;
  isIcDepth?: boolean;
  shareUnlocked?: boolean;
  /** When free/instant/preview/missing, hard-cap UI to Free — beats sticky Pro invent */
  researchDepth?: string | null;
  preview?: boolean;
}): ResultsLadder {
  const demo = input.demoTier || null;
  const owned = new Set(
    (input.entitlementTiers || []).map((t) => String(t || '').toLowerCase()).filter(Boolean)
  );
  const stamped = normalizeAccessTier(input.accessTier);
  const depthCap = ladderTierFromResearchDepth(input.researchDepth, input.preview);

  // Display tier = THIS run's depth (sample parity). Sticky entitlements never invent higher.
  let tier: ResultsLadderTier = 'free';
  if (demo === 'pro') tier = 'pro';
  else if (demo === 'partner') tier = 'partner';
  else if (demo === 'free') tier = 'free';
  else if (depthCap === 'free') {
    tier = 'free';
  } else if (depthCap === 'partner') {
    tier = 'partner';
  } else if (depthCap === 'pro') {
    // Pro-depth desk. IC package only when this run is actually IC depth (isIcDepth),
    // not merely because email has an old IC purchase stamp.
    if (input.isIcDepth && (stamped === 'ic' || ['ic_project', 'ic_consultant', 'ic_annual', 'sponsor'].some((t) => owned.has(t)))) {
      tier = 'ic';
    } else {
      tier = 'pro';
    }
  } else if (depthCap === 'ic') {
    tier = 'ic';
  } else {
    // Unknown → Free soft-lock (never invent Pro/IC from entitlements alone)
    tier = 'free';
  }

  const ownsIc = tier === 'ic';
  const ownsPro = tier === 'pro' || ownsIc;
  const ownsPartner = tier === 'partner' || ownsPro;
  const allowProDesk = ownsPro;
  const blurProDesk = !allowProDesk;
  const ownsIcAnnual = owned.has('ic_annual');

  // Match sample Free: always soft-locked paywall theater (share unlock does not clear blur).
  const softLocked =
    demo === 'free'
      ? true
      : demo === 'partner' || demo === 'pro'
        ? false
        : tier === 'free';

  let punchVisible: number;
  let findingsVisible: number;
  if (softLocked) {
    punchVisible = FREE_SOFT_PUNCH;
    findingsVisible = FREE_SOFT_FINDINGS;
  } else if (ownsPro) {
    punchVisible = PRO_PUNCH;
    findingsVisible = PRO_FINDINGS;
  } else if (tier === 'partner') {
    punchVisible = PARTNER_PUNCH;
    findingsVisible = PARTNER_FINDINGS;
  } else {
    // Free after share — strictly less than Estimator
    punchVisible = FREE_UNLOCKED_PUNCH;
    findingsVisible = FREE_UNLOCKED_FINDINGS;
  }

  // Tease Pro desk formats on Free only — Estimator already owns unlocked punch.
  const proBlurPunchTeasers = tier === 'free' && !softLocked && !ownsPro ? 2 : 0;
  const syntheticBlurTeasers = softLocked ? FREE_SYNTHETIC_BLUR_TEASERS : 0;

  return {
    tier,
    softLocked,
    punchVisible,
    findingsVisible,
    ownsPartner,
    ownsPro,
    ownsIc,
    ownsIcAnnual,
    allowProDesk,
    blurProDesk,
    proBlurPunchTeasers,
    syntheticBlurTeasers,
  };
}
