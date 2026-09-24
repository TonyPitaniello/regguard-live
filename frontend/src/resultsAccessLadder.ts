/**
 * Free → Estimator → Pro access ladder for Site Diligence Results.
 * Used by sample demos and live entitlement gating.
 */

export type ResultsLadderTier = 'free' | 'partner' | 'pro' | 'ic';

export type ResultsLadder = {
  tier: ResultsLadderTier;
  /** Free soft-lock: limited punch + blurred cost until share/upgrade */
  softLocked: boolean;
  punchVisible: number;
  findingsVisible: number;
  ownsPartner: boolean;
  ownsPro: boolean;
  ownsIc: boolean;
  allowProDesk: boolean;
  /** Blur Pro desk / city pack / CSV chrome */
  blurProDesk: boolean;
  /** How many trailing punch lines to show as Pro-blurred teasers (partner) */
  proBlurPunchTeasers: number;
};

const FREE_PUNCH = 3;
const PARTNER_PUNCH = 8;
const FREE_FINDINGS = 3;
const PARTNER_FINDINGS = 8;

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
  const stamped = String(input.accessTier || '').toLowerCase().trim();

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
    stamped === 'contractor_pro' ||
    owned.has('contractor_pro') ||
    sessionTier.includes('contractor_pro')
  ) {
    tier = 'pro';
  } else if (stamped === 'partner' || owned.has('partner') || sessionTier.includes('partner')) {
    tier = 'partner';
  } else {
    tier = 'free';
  }

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
    allowProDesk,
    blurProDesk,
    proBlurPunchTeasers,
  };
}
