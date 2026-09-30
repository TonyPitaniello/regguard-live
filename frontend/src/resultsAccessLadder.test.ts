/**
 * Node-style smoke checks for sample-parity ladder
 * (run: npx tsx src/resultsAccessLadder.test.ts)
 */
import {
  resolveResultsLadder,
  ladderUpsells,
  ladderTierFromResearchDepth,
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

// Missing depth + sticky IC must NOT invent IC (was Free→IC skip bug)
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
  const rows = ladderUpsells(ladder.tier, { nextOnly: true });
  assert(rows.length === 1 && rows[0].tier === 'partner', 'missing depth next = Estimator only');
}

// Sticky IC stamp on free preview flag
{
  const ladder = resolveResultsLadder({
    accessTier: 'ic_project',
    entitlementTiers: ['ic_project'],
    preview: true,
  });
  assert(ladder.tier === 'free', 'preview flag caps at free over IC stamp');
  assert(ladderUpsells(ladder.tier)[0].tier === 'partner', 'preview free → Estimator');
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
  assert(ladder.softLocked === false, 'Estimator not soft-locked');
  assert(ladderUpsells('partner')[0].tier === 'contractor_pro', 'Estimator next = Pro');
}

// Pro-depth unlocks desk; next upsell is IC — sticky IC stamp alone does not flip display to IC
{
  const ladder = resolveResultsLadder({
    accessTier: 'ic',
    entitlementTiers: ['ic_project', 'contractor_pro'],
    researchDepth: 'pro',
    isIcDepth: false,
  });
  assert(ladder.tier === 'pro', 'pro depth stays Pro without isIcDepth');
  assert(ladder.allowProDesk === true, 'Pro allows desk');
  assert(ladder.blurProDesk === false, 'Pro no desk blur');
  const rows = ladderUpsells('pro', { nextOnly: true });
  assert(rows.length === 1 && rows[0].tier === 'ic_project', 'Pro next = IC only');
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

// Soft-locked free
{
  const ladder = resolveResultsLadder({
    accessTier: 'free',
    entitlementTiers: [],
    shareUnlocked: false,
  });
  assert(ladder.softLocked === true, 'free soft-locks');
  assert(ladder.punchVisible === FREE_SOFT_PUNCH, 'soft punch');
}

// Sample free always soft-locked
{
  const ladder = resolveResultsLadder({
    demoTier: 'free',
    shareUnlocked: true,
    entitlementTiers: ['contractor_pro'],
  });
  assert(ladder.tier === 'free', 'sample free tier');
  assert(ladder.softLocked === true, 'sample free stays soft-locked');
}

// Sample partner matches Estimator desk blur
{
  const ladder = resolveResultsLadder({ demoTier: 'partner' });
  assert(ladder.tier === 'partner', 'sample partner');
  assert(ladder.blurProDesk === true, 'sample partner blurs desk');
  assert(ladder.softLocked === false, 'sample partner unlocked punch');
}

// Sample pro unlocks desk
{
  const ladder = resolveResultsLadder({ demoTier: 'pro' });
  assert(ladder.tier === 'pro', 'sample pro');
  assert(ladder.allowProDesk === true, 'sample pro desk');
}

// Free upsell is Estimator only (next step)
{
  const rows = ladderUpsells('free', { nextOnly: true });
  assert(rows.length === 1 && rows[0].tier === 'partner', 'free next = partner only');
}

// Estimator upsell is Pro only
{
  const rows = ladderUpsells('partner', { nextOnly: true });
  assert(rows.length === 1 && rows[0].tier === 'contractor_pro', 'partner next = pro');
}

// Explicit partner depth is not free even with preview leftover
{
  assert(
    ladderTierFromResearchDepth('partner', true) === 'partner',
    'partner depth beats preview flag'
  );
  assert(ladderTierFromResearchDepth('pro', true) === 'pro', 'pro depth beats preview flag');
  assert(ladderTierFromResearchDepth('', false) === 'free', 'empty depth = free');
}

console.log('resultsAccessLadder.test.ts OK');
