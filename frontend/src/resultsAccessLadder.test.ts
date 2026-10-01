/**
 * Node-style smoke checks for sample-parity ladder
 * (run: npx tsx src/resultsAccessLadder.test.ts)
 */
import {
  resolveResultsLadder,
  ladderUpsells,
  ladderTierFromResearchDepth,
  downloadsAllowedForTier,
  FREE_SOFT_PUNCH,
  FREE_SYNTHETIC_BLUR_TEASERS,
} from './resultsAccessLadder';

function assert(cond: unknown, msg: string) {
  if (!cond) throw new Error(msg);
}

// Sticky Pro invent must NOT unlock a free-depth run
{
  const ladder = resolveResultsLadder({
    accessTier: 'contractor_pro',
    entitlementTiers: ['contractor_pro', 'partner'],
    shareUnlocked: true,
    researchDepth: 'free',
  });
  assert(ladder.tier === 'free', 'free research_depth must beat sticky Pro access_tier');
  assert(ladder.blurProDesk === true, 'free depth must blur Pro desk');
  assert(ladder.allowProDesk === false, 'free depth must not allow Pro desk');
  assert(ladder.softLocked === true, 'live free always soft-locked like sample');
  assert(ladder.punchVisible === FREE_SOFT_PUNCH, 'free soft punch');
  assert(ladder.syntheticBlurTeasers === FREE_SYNTHETIC_BLUR_TEASERS, 'free synthetic blur');
}

// Missing depth + sticky IC must NOT invent IC
{
  const ladder = resolveResultsLadder({
    accessTier: 'ic',
    entitlementTiers: ['ic_project', 'contractor_pro'],
    shareUnlocked: true,
    researchDepth: '',
    preview: false,
  });
  assert(ladder.tier === 'free', 'missing depth defaults to free — never invent IC');
  assert(ladder.softLocked === true, 'missing depth soft-locks');
  assert(ladder.blurProDesk === true, 'missing depth blurs desk');
}

// Free upsells: next → highest (Estimator, Pro, IC, Annual)
{
  const rows = ladderUpsells('free');
  assert(rows.length >= 3, 'free lists multiple higher tiers');
  assert(rows[0].tier === 'partner' && rows[0].primary, 'free primary = Estimator');
  assert(rows.some((r) => r.tier === 'contractor_pro'), 'free includes Pro');
  assert(rows.some((r) => r.tier === 'ic_project'), 'free includes IC Project');
  assert(rows.some((r) => r.tier === 'ic_annual'), 'free includes IC Annual');
}

// Estimator upsells: Pro → IC → Annual
{
  const rows = ladderUpsells('partner');
  assert(rows[0].tier === 'contractor_pro' && rows[0].primary, 'partner primary = Pro');
  assert(rows.some((r) => r.tier === 'ic_project'), 'partner includes IC');
  assert(rows.some((r) => r.tier === 'ic_annual'), 'partner includes Annual');
  assert(!rows.some((r) => r.tier === 'partner'), 'partner does not re-sell Estimator');
}

// Pro upsells: IC then Annual
{
  const rows = ladderUpsells('pro');
  assert(rows[0].tier === 'ic_project' && rows[0].primary, 'pro primary = IC');
  assert(rows.some((r) => r.tier === 'ic_annual'), 'pro includes Annual');
}

// nextOnly still works for single CTA
{
  const rows = ladderUpsells('free', { nextOnly: true });
  assert(rows.length === 1 && rows[0].tier === 'partner', 'nextOnly free = partner only');
}

// Downloads commensurate with paid tier
{
  const free = downloadsAllowedForTier('free');
  assert(free.receiptPreview && !free.receiptHabit && !free.proDesk && !free.icBundle, 'free downloads');
  const partner = downloadsAllowedForTier('partner');
  assert(partner.receiptHabit && !partner.proDesk && !partner.icBundle, 'estimator downloads');
  const pro = downloadsAllowedForTier('pro');
  assert(pro.proDesk && !pro.icBundle, 'pro downloads');
  const ic = downloadsAllowedForTier('ic');
  assert(ic.proDesk && ic.icBundle, 'ic downloads');
}

// Sticky Pro entitlements must NOT unlock a server-stamped free run
{
  const ladder = resolveResultsLadder({
    accessTier: 'free',
    entitlementTiers: ['contractor_pro', 'partner'],
    shareUnlocked: true,
  });
  assert(ladder.tier === 'free', 'free stamp must win over sticky Pro');
  assert(ladder.blurProDesk === true, 'free must blur Pro desk');
  assert(ladder.softLocked === true, 'free soft-locked');
}

// Estimator-depth must NOT unlock Pro desk from sticky contractor_pro
{
  const ladder = resolveResultsLadder({
    accessTier: 'contractor_pro',
    entitlementTiers: ['contractor_pro'],
    researchDepth: 'partner',
  });
  assert(ladder.tier === 'partner', 'partner depth caps at Estimator');
  assert(ladder.blurProDesk === true, 'Estimator blurs Pro desk');
  assert(ladder.allowProDesk === false, 'Estimator no Pro desk downloads');
}

// Pro-depth unlocks desk
{
  const ladder = resolveResultsLadder({
    accessTier: 'contractor_pro',
    entitlementTiers: ['contractor_pro'],
    researchDepth: 'pro',
    isIcDepth: false,
  });
  assert(ladder.tier === 'pro', 'pro depth');
  assert(ladder.allowProDesk === true, 'Pro allows desk');
}

// Sample free / partner / pro
{
  assert(resolveResultsLadder({ demoTier: 'free' }).softLocked === true, 'sample free soft');
  assert(resolveResultsLadder({ demoTier: 'partner' }).blurProDesk === true, 'sample partner blur');
  assert(resolveResultsLadder({ demoTier: 'pro' }).allowProDesk === true, 'sample pro desk');
}

assert(ladderTierFromResearchDepth('partner', true) === 'partner', 'partner beats preview');
assert(ladderTierFromResearchDepth('', false) === 'free', 'empty = free');

console.log('resultsAccessLadder.test.ts OK');
