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
 */

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

/** Highest entitlement wins — used when stamping live scan results. */
export function accessTierFromEntitlements(tiers: string[] | undefined | null): ResultsLadderTier {
  const owned = new Set((tiers || []).map((t) => String(t || '').toLowerCase()).filter(Boolean));
  if (['ic_project', 'ic_consultant', 'ic_annual', 'sponsor'].some((t) => owned.has(t))) return 'ic';
  if (owned.has('contractor_pro')) return 'pro';
  if (owned.has('partner')) return 'partner';
  return 'free';
}

/**
 * Next-step checkout CTAs for blurred / locked sections.
 * Free → Estimator → Pro → IC Project → IC Annual (one step at a time).
 */
export function ladderUpsells(
  tier: ResultsLadderTier,
  opts?: { ownsIcAnnual?: boolean; nextOnly?: boolean }
): LadderUpsell[] {
  const nextOnly = opts?.nextOnly !== false;
  if (tier === 'free') {
    const rows: LadderUpsell[] = [
      {
        tier: 'partner',
        label: 'Estimator / Permit Runner — $79/mo',
        offers: 'Full Bid Risk Receipt habit · unlocked punch · Saved Jobs',
        primary: true,
      },
    ];
    if (!nextOnly) {
      rows.push({
        tier: 'contractor_pro',
        label: 'Contractor Pro — $149/mo',
        offers: 'Deep scout · fee $ · City Pack PDF · CSV · bid packet',
      });
    }
    return rows;
  }
  if (tier === 'partner') {
    return [
      {
        tier: 'contractor_pro',
        label: 'Contractor Pro — $149/mo',
        offers: 'Deep scout · fee dollars · City Pack PDF · CSV · bid packet',
        primary: true,
      },
    ];
  }
  if (tier === 'pro') {
    const rows: LadderUpsell[] = [
      {
        tier: 'ic_project',
        label: 'IC Diligence Bundle — $1,500',
        offers: 'Counsel ZIP: memo · boardroom PDF · DOCX · Excel evidence',
        primary: true,
      },
    ];
    if (!nextOnly && !opts?.ownsIcAnnual) {
      rows.push({
        tier: 'ic_annual',
        label: 'IC Annual — $15,000/yr',
        offers: 'Multi-site Diligence Bundle regenerations',
      });
    }
    return rows;
  }
  if (opts?.ownsIcAnnual) {
    return [
      {
        tier: 'ic_project',
        label: 'Another site IC Bundle — $1,500',
        offers: 'Same counsel ZIP for a new bound address',
        primary: true,
      },
    ];
  }
  return [
    {
      tier: 'ic_annual',
      label: 'IC Annual — multi-site — $15,000/yr',
      offers: 'Regenerate Diligence Bundles across many sites',
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
}): ResultsLadder {
  const demo = input.demoTier || null;
  const owned = new Set(
    (input.entitlementTiers || []).map((t) => String(t || '').toLowerCase()).filter(Boolean)
  );
  const stamped = normalizeAccessTier(input.accessTier);

  // Never unlock from sessionStorage alone — abandoned checkout sticky Pro bug.
  let tier: ResultsLadderTier = 'free';
  if (demo === 'pro') tier = 'pro';
  else if (demo === 'partner') tier = 'partner';
  else if (demo === 'free') tier = 'free';
  else if (
    stamped === 'ic' ||
    ['ic_project', 'ic_consultant', 'ic_annual', 'sponsor'].some((t) => owned.has(t))
  ) {
    tier = 'ic';
  } else if (stamped === 'pro' || owned.has('contractor_pro')) {
    tier = 'pro';
  } else if (stamped === 'partner' || owned.has('partner')) {
    tier = 'partner';
  } else {
    tier = 'free';
  }

  const ownsIc = tier === 'ic';
  const ownsPro = tier === 'pro' || ownsIc;
  const ownsPartner = tier === 'partner' || ownsPro;
  const allowProDesk = ownsPro;
  const blurProDesk = !allowProDesk;
  const ownsIcAnnual = owned.has('ic_annual');

  // Sample Free stays soft-locked so the demo shows the paywall theater.
  // Live Free soft-locks until share unlock.
  const softLocked =
    demo === 'free'
      ? true
      : demo === 'partner' || demo === 'pro'
        ? false
        : tier === 'free' && !input.shareUnlocked;

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
  };
}
