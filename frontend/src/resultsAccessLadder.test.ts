/**
 * Node-style smoke checks for free-run ladder (run: npx tsx src/resultsAccessLadder.test.ts)
 */
import {
  resolveResultsLadder,
  ladderUpsells,
  FREE_SOFT_PUNCH,
  FREE_UNLOCKED_PUNCH,
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
  assert(ladder.allowProDesk === false, 'free must not allow Pro desk');
  assert(ladder.softLocked === false, 'share unlock clears soft-lock for punch');
  assert(ladder.punchVisible === FREE_UNLOCKED_PUNCH, 'free after share punch cap');
}

// Soft-locked free
{
  const ladder = resolveResultsLadder({
    accessTier: 'free',
    entitlementTiers: [],
    shareUnlocked: false,
  });
  assert(ladder.softLocked === true, 'free soft-locks without share');
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

// Free upsell is Estimator only (next step)
{
  const rows = ladderUpsells('free', { nextOnly: true });
  assert(rows.length === 1 && rows[0].tier === 'partner', 'free next = partner only');
}

console.log('resultsAccessLadder.test.ts OK');
