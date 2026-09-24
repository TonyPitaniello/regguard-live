/**
 * Free → Estimator → Pro → IC → IC Annual access ladder for Site Diligence Results.
 * Used by sample demos and live entitlement gating on every new scan.
 */

export type ResultsLadderTier = 'free' | 'partner' | 'pro' | 'ic';

export type CheckoutLadderTier = 'partner' | 'contractor_pro' | 'ic_project' | 'ic_annual';

export type ResultsLadder = {
  tier: ResultsLadderTier;
  /** Free soft-lock: limited punch + blurred cost until share/upgrade */
  softLocked: boolean;
  punchVisible: number;
  findingsVisible: number;
  ownsPartner: boolean;
  ownsPro: boolean;
  ownsIc: boolean;
  ownsIcAnnual: boolean;
  allowProDesk: boolean;
  /** Blur Pro desk / city pack / CSV chrome */
  blurProDesk: boolean;
  /** How many trailing punch lines to show as Pro-blurred teasers (partner) */
  proBlurPunchTeasers: number;
};

export type LadderUpsell = {
  tier: CheckoutLadderTier;
  label: string;
  primary?: boolean;
};

const FREE_PUNCH = 3;
const PARTNER_PUNCH = 8;
const FREE_FINDINGS = 3;
const PARTNER_FINDINGS = 8;

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
 * Free → Estimator → Pro → IC Project → IC Annual.
 */
export function ladderUpsells(
  tier: ResultsLadderTier,
  opts?: { ownsIcAnnual?: boolean; includeIcOnFree?: boolean }
): LadderUpsell[] {
  if (tier === 'free') {
    const rows: LadderUpsell[] = [
      { tier: 'partner', label: 'Estimator / Permit Runner — $79/mo', primary: true },
      { tier: 'contractor_pro', label: 'Contractor Pro — $149/mo' },
    ];
    if (opts?.includeIcOnFree !== false) {
      rows.push({ tier: 'ic_project', label: 'IC Diligence Bundle — $1,500' });
    }
    return rows;
  }
  if (tier === 'partner') {
    return [
      { tier: 'contractor_pro', label: 'Contractor Pro — $149/mo', primary: true },
      { tier: 'ic_project', label: 'IC Diligence Bundle — $1,500' },
    ];
  }
  if (tier === 'pro') {
    return [
      { tier: 'ic_project', label: 'IC Diligence Bundle — $1,500', primary: true },
      { tier: 'ic_annual', label: 'IC Annual — $15,000/yr' },
    ];
  }
  // IC depth / IC Project owners
  if (opts?.ownsIcAnnual) {
    return [{ tier: 'ic_project', label: 'Another site IC Bundle — $1,500', primary: true }];
  }
  return [
    { tier: 'ic_annual', label: 'IC Annual — multi-site — $15,000/yr', primary: true },
    { tier: 'ic_project', label: 'Another site IC Bundle — $1,500' },
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
  const sessionTier =
    typeof window !== 'undefined'
      ? (sessionStorage.getItem('regguardTier') || '').toLowerCase()
      : '';
  const stamped = normalizeAccessTier(input.accessTier);
  const ownsIcAnnual = owned.has('ic_annual') || sessionTier.includes('ic_annual');

  let tier: ResultsLadderTier = 'free';
  if (demo === 'pro') tier = 'pro';
  else if (demo === 'partner') tier = 'partner';
  else if (demo === 'free') tier = 'free';
  else if (
    input.isIcDepth ||
    stamped === 'ic' ||
    ['ic_project', 'ic_consultant', 'ic_annual', 'sponsor'].some((t) => owned.has(t))
  ) {
    tier = 'ic';
  } else if (
    stamped === 'pro' ||
    owned.has('contractor_pro') ||
    sessionTier.includes('contractor_pro')
  ) {
    tier = 'pro';
  } else if (stamped === 'partner' || owned.has('partner') || sessionTier.includes('partner')) {
    tier = 'partner';
  } else {
    tier = 'free';
  }

  // Never grant Pro desk from research depth alone — entitlement / stamp only.
  const ownsIc = tier === 'ic';
  const ownsPro = tier === 'pro' || ownsIc;
  const ownsPartner = tier === 'partner' || ownsPro;
  const allowProDesk = ownsPro;
  const blurProDesk = !allowProDesk;

  // Free: most blur until share unlocks the rest of the free list (still no Pro desk).
  const softLocked =
    demo === 'free'
      ? true
      : demo === 'partner' || demo === 'pro'
        ? false
        : tier === 'free' && !input.shareUnlocked;

  const punchVisible = softLocked
    ? FREE_PUNCH
    : tier === 'partner'
      ? PARTNER_PUNCH
      : ownsPro
        ? 99
        : // free after share unlock — full free punch list
          99;

  const findingsVisible = softLocked
    ? FREE_FINDINGS
    : tier === 'partner'
      ? PARTNER_FINDINGS
      : 12;

  const proBlurPunchTeasers = tier === 'partner' && !ownsPro ? 2 : 0;

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
