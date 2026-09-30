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
 * Upsell: each level points to the *next* level only — never Free → IC skip.
 *
 * HARD RULE: display tier comes from THIS run's research_depth / demoTier.
 * Sticky entitlements must NEVER invent Pro/IC on a free or missing-depth run.
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
  /** Short “what you get” line for the next step */
  offers?: string;
  primary?: boolean;
};

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
 * Next-step checkout CTAs — pain-first copy from TIER_VOICE (one step only).
 */
export function ladderUpsells(
  tier: ResultsLadderTier,
  opts?: { ownsIcAnnual?: boolean; nextOnly?: boolean }
): LadderUpsell[] {
  const nextOnly = opts?.nextOnly !== false;
  if (tier === 'free') {
    const v = TIER_VOICE.free;
    const rows: LadderUpsell[] = [
      {
        tier: 'partner',
        label: v.upsellCta,
        offers: v.upsellOffers,
        primary: true,
      },
    ];
    if (!nextOnly) {
      rows.push({
        tier: 'contractor_pro',
        label: TIER_VOICE.partner.upsellCta,
        offers: TIER_VOICE.partner.upsellOffers,
      });
    }
    return rows;
  }
  if (tier === 'partner') {
    const v = TIER_VOICE.partner;
    return [
      {
        tier: 'contractor_pro',
        label: v.upsellCta,
        offers: v.upsellOffers,
        primary: true,
      },
    ];
  }
  if (tier === 'pro') {
    const v = TIER_VOICE.pro;
    const rows: LadderUpsell[] = [
      {
        tier: 'ic_project',
        label: v.upsellCta,
        offers: v.upsellOffers,
        primary: true,
      },
    ];
    if (!nextOnly && !opts?.ownsIcAnnual) {
      rows.push({
        tier: 'ic_annual',
        label: TIER_VOICE.ic.upsellCta,
        offers: TIER_VOICE.ic.upsellOffers,
      });
    }
    return rows;
  }
  const next = nextVoiceForLadderTier('ic', { ownsIcAnnual: opts?.ownsIcAnnual });
  if (opts?.ownsIcAnnual) {
    return [
      {
        tier: 'ic_project',
        label: next.upsellCta,
        offers: next.upsellOffers,
        primary: true,
      },
    ];
  }
  return [
    {
      tier: 'ic_annual',
      label: TIER_VOICE.ic.upsellCta,
      offers: TIER_VOICE.ic.upsellOffers,
      primary: true,
    },
  ];
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
