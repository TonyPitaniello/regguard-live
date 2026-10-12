/**
 * Sample ladder demos — Free (least + blur) → Estimator (more) → Pro (full Pro desk).
 * Applied on /sample-site-diligence?tier=…
 */

import type { AnalysisData } from './ResultsViewerModal';
import {
  FREE_SOFT_PUNCH,
  PARTNER_PUNCH,
  PRO_PUNCH,
  resolveResultsLadder,
  type ResultsLadder,
} from './resultsAccessLadder';

export type SampleDemoTier = 'free' | 'partner' | 'pro' | 'ic';

/** Must stay identical to resolveResultsLadder punchVisible for each demo tier. */
export const SAMPLE_DEMO_PUNCH_VISIBLE: Record<SampleDemoTier, number> = {
  free: FREE_SOFT_PUNCH,
  partner: PARTNER_PUNCH,
  pro: PRO_PUNCH,
  ic: PRO_PUNCH,
};

/** Canonical sample ↔ live visibility matrix (demoTier and researchDepth must agree). */
export function ladderVisibilityForSampleTier(tier: SampleDemoTier): ResultsLadder {
  return resolveResultsLadder({ demoTier: tier });
}

export function ladderVisibilityForLiveDepth(tier: SampleDemoTier): ResultsLadder {
  const depth =
    tier === 'free'
      ? 'free'
      : tier === 'partner'
        ? 'partner'
        : tier === 'pro'
          ? 'pro'
          : 'ic';
  return resolveResultsLadder({
    researchDepth: depth,
    preview: tier === 'free',
    isDeep: tier === 'pro' || tier === 'ic',
    isIcDepth: tier === 'ic',
    accessTier:
      tier === 'free'
        ? 'free'
        : tier === 'partner'
          ? 'partner'
          : tier === 'pro'
            ? 'contractor_pro'
            : 'ic',
  });
}

const EXTRA_PUNCH = [
  {
    priority: 'MEDIUM',
    task: 'Verify trade fee line-items on Fort Worth schedule (do not reuse Dallas/Plano numbers)',
    owner: 'Estimator',
    due_window: 'Week 1',
    timeline: 'Week 1',
    trade: 'ELECTRICAL',
    estimated_cost: 0,
    verified: true,
    source_url:
      'https://www.fortworthtexas.gov/files/assets/public/v/9/development-services/documents/resources-applications-forms-videos/f/development-fees-schedule.pdf',
    source_label: 'Fort Worth fee schedule',
  },
  {
    priority: 'MEDIUM',
    task: 'Confirm zoning / land-use path with Fort Worth planning (industrial or DC use)',
    owner: 'PM / Zoning',
    due_window: 'Pre-bid',
    timeline: 'Pre-bid',
    trade: 'GENERAL',
    verified: false,
    source_url: 'https://www.fortworthtexas.gov/departments/development-services',
    source_label: 'Fort Worth Development Services',
  },
  {
    priority: 'MEDIUM',
    task: 'Add day-7 re-check reminder before bid due date',
    owner: 'PM / Estimator',
    due_window: 'Pre-bid',
    timeline: 'Pre-bid',
    trade: 'GENERAL',
    verified: false,
  },
  {
    priority: 'LOW',
    task: 'Attach Accela CFW receipt / application # to the bid file',
    owner: 'Permit runner',
    due_window: 'Week 2',
    timeline: 'Week 2',
    trade: 'GENERAL',
    verified: true,
    source_url: 'https://aca-prod.accela.com/CFW',
  },
  {
    priority: 'LOW',
    task: 'Note inspection sequence: rough MEP → service → final',
    owner: 'GC',
    due_window: 'Construction',
    timeline: 'Construction',
    trade: 'GENERAL',
    verified: true,
    source_url: 'https://www.fortworthtexas.gov/departments/development-services',
  },
  {
    priority: 'LOW',
    task: 'Attach FIRMette + NWI screenshot to the Bid Risk Receipt forward',
    owner: 'Estimator',
    due_window: 'Week 1',
    timeline: 'Week 1',
    trade: 'GENERAL',
    verified: true,
    source_url: 'https://msc.fema.gov/portal/home',
    source_label: 'FEMA MSC',
  },
] as const;

export function parseSampleDemoTier(raw: string | null | undefined): SampleDemoTier | null {
  const t = String(raw || '').toLowerCase().trim();
  if (t === 'free' || t === 'partner' || t === 'pro' || t === 'ic') return t;
  if (t === 'estimator' || t === 'permit' || t === 'permit_runner') return 'partner';
  if (t === 'contractor_pro' || t === 'contractor-pro') return 'pro';
  if (t === 'ic_project' || t === 'diligence' || t === 'counsel') return 'ic';
  return null;
}

/** Clone Chapin sample analysis into Free / Estimator / Pro depth shapes. */
export function analysisForSampleDemo(
  base: AnalysisData,
  tier: SampleDemoTier | null
): AnalysisData {
  if (!tier) return base;
  const clone = structuredClone(base) as AnalysisData;
  const punch = [...(clone.punch_list?.punch_list || [])];
  for (const row of EXTRA_PUNCH) {
    punch.push({ ...row });
  }
  if (clone.punch_list) clone.punch_list = { ...clone.punch_list, punch_list: punch };
  else clone.punch_list = { punch_list: punch };

  // Keep parcel pin so Environmental Findings do not show incomplete GIS
  const pi = clone.project_info || ({} as AnalysisData['project_info']);
  if (pi.latitude == null && (pi as { lat?: number }).lat != null) {
    pi.latitude = (pi as { lat?: number }).lat;
  }
  if (pi.longitude == null && (pi as { lng?: number }).lng != null) {
    pi.longitude = (pi as { lng?: number }).lng;
  }
  clone.project_info = pi;

  if (tier === 'free') {
    clone.depth_tier = 'free';
    clone.research_depth = 'free';
    clone.depth_badge = 'SAMPLE — Free Lookups Preview';
    clone.ic_package = false;
    clone.research_incomplete = false;
    clone.depth_claim_honest = true;
    clone.scout_mode = 'none';
    clone.preview = true;
    (clone as AnalysisData & { receipt_mode?: string }).receipt_mode = 'free_preview';
    (clone as AnalysisData & { soft_lock_contingency?: boolean }).soft_lock_contingency = true;
    if (clone.punch_list) {
      clone.punch_list = { ...clone.punch_list, habit_unlocked: false };
    }
    clone.depth_claim_note =
      'Free preview — shape of risk only. Estimator unlocks contingency + full punch you can forward.';
  } else if (tier === 'partner') {
    clone.depth_tier = 'partner';
    clone.research_depth = 'partner';
    clone.depth_badge = 'SAMPLE — Estimator / Permit Runner';
    clone.ic_package = false;
    clone.research_incomplete = false;
    clone.depth_claim_honest = true;
    clone.scout_mode = 'none';
    clone.preview = false;
    (clone as AnalysisData & { receipt_mode?: string }).receipt_mode = 'estimator_habit';
    (clone as AnalysisData & { soft_lock_contingency?: boolean }).soft_lock_contingency = false;
    if (clone.punch_list) {
      clone.punch_list = { ...clone.punch_list, habit_unlocked: true };
    }
    clone.depth_claim_note =
      'Estimator habit Receipt — full contingency + unlocked punch. Contractor Pro adds fee dollars and City Pack PDF.';
  } else if (tier === 'pro') {
    clone.depth_tier = 'pro_light';
    clone.research_depth = 'pro';
    clone.depth_badge = 'SAMPLE — Contractor Pro — Local Confirm + Light Scout';
    clone.ic_package = false;
    clone.research_incomplete = false;
    clone.depth_claim_honest = true;
    clone.scout_mode = 'light';
    clone.preview = false;
    (clone as AnalysisData & { receipt_mode?: string }).receipt_mode = 'estimator_habit';
    (clone as AnalysisData & { soft_lock_contingency?: boolean }).soft_lock_contingency = false;
    if (clone.punch_list) {
      clone.punch_list = { ...clone.punch_list, habit_unlocked: true };
    }
    clone.depth_claim_note =
      'Contractor Pro — fee dollars and City Pack open. IC Diligence Bundle adds the counsel ZIP.';
  } else {
    clone.depth_tier = 'ic_full';
    clone.research_depth = 'ic';
    clone.depth_badge = 'SAMPLE — IC Diligence Bundle';
    clone.ic_package = true;
    clone.research_incomplete = false;
    clone.depth_claim_honest = true;
    clone.scout_mode = 'full';
    clone.preview = false;
    (clone as AnalysisData & { receipt_mode?: string }).receipt_mode = 'estimator_habit';
    (clone as AnalysisData & { soft_lock_contingency?: boolean }).soft_lock_contingency = false;
    if (clone.punch_list) {
      clone.punch_list = { ...clone.punch_list, habit_unlocked: true };
    }
    clone.depth_claim_note =
      'IC Diligence Bundle — counsel ZIP open (memo, boardroom, Word, Excel). Same Pro desk underneath.';
  }

  clone.research_id = `rg-sample-chapin-${tier}`;
  clone.sample_demo_tier = tier;
  const access =
    tier === 'ic' ? 'ic' : tier === 'pro' ? 'contractor_pro' : tier === 'partner' ? 'partner' : 'free';
  (clone as AnalysisData & { access_tier?: string }).access_tier = access;
  (clone as AnalysisData & { entitlement_tiers?: string[] }).entitlement_tiers =
    tier === 'free'
      ? []
      : tier === 'partner'
        ? ['partner']
        : tier === 'pro'
          ? ['contractor_pro', 'partner']
          : ['ic_project', 'contractor_pro', 'partner'];
  // Stepwise next-level CTA on every sample (never Free → IC)
  clone.upgrade_offer = sampleUpgradeOffer(tier);
  return clone;
}

/** Sample / live-shaped next-step offer — from TIER_VOICE */
export function sampleUpgradeOffer(tier: SampleDemoTier): NonNullable<AnalysisData['upgrade_offer']> {
  // Keep samples in lockstep with frontend/src/tierVoice.ts
  if (tier === 'free') {
    return {
      message: 'Stop re-sending screenshots that fall apart in the GC thread',
      detail:
        'You’re still on Free: shape of risk, nothing the GC can file. Estimator / Permit Runner ($79/mo) gives you the full Bid Risk Receipt you can forward, the rest of the punch list, and Saved Jobs.',
      cta_label: 'Start Estimator / Permit Runner — $79/mo',
      cta_tier: 'partner',
      secondary_cta_label: undefined,
      secondary_cta_tier: undefined,
      current_label: 'Free Lookups',
      next_label: 'Estimator — forwardable Receipt · full punch · Saved Jobs',
      primary_once: true,
      honesty_note: 'Climb one step — City Pack and counsel ZIP stay further up the ladder.',
    };
  }
  if (tier === 'partner') {
    return {
      message: 'Still hunting fee dollars and city schedules by hand?',
      detail:
        'Estimator got you a Receipt the GC can file. Contractor Pro ($149/mo) puts fee dollars, Full City Pack PDF, paste-ready CSV, and bid packet on the desk — for jobs where your number has to hold.',
      cta_label: 'Upgrade to Contractor Pro — $149/mo',
      cta_tier: 'contractor_pro',
      secondary_cta_label: undefined,
      secondary_cta_tier: undefined,
      current_label: 'Estimator / Permit Runner',
      next_label: 'Pro bid desk — fee dollars · City Pack PDF · CSV · bid packet',
      primary_once: true,
      honesty_note: 'Pro arms the estimate — still confirm dollars on the live AHJ schedule.',
    };
  }
  if (tier === 'pro') {
    return {
      message: 'Counsel won’t mark up a City Pack PDF',
      detail:
        'Pro is the bid desk. For one capital-sensitive address — LOI, IC call, owner’s rep, lender — IC Diligence Bundle ($1,500) ships the counsel ZIP: memo, boardroom, Word with exhibits, Excel evidence. Not a bigger City Pack.',
      cta_label: 'Get IC Diligence Bundle — $1,500',
      cta_tier: 'ic_project',
      secondary_cta_label: undefined,
      secondary_cta_tier: undefined,
      current_label: 'Contractor Pro',
      next_label: 'Counsel ZIP — memo · boardroom · Word · Excel exhibits',
      primary_once: true,
      honesty_note: 'IC is counsel packaging for one site — not an AHJ filing.',
    };
  }
  return {
    message: 'Buying another $1,500 Project for the next capital site?',
    detail:
      'You proved the package on one site. If you will package Diligence Bundles on more capital sites this year, IC Annual ($15,000/yr) covers those ZIPs on this purchase email — ahead of Project rate once you pass about ~10 sites.',
    cta_label: 'IC Annual — $15,000/yr',
    cta_tier: 'ic_annual',
    secondary_cta_label: undefined,
    secondary_cta_tier: undefined,
    current_label: 'IC Diligence Bundle',
    next_label: 'Same counsel ZIP · new capital site · no new $1,500 PO',
    primary_once: true,
    honesty_note: 'Annual covers capital-site counsel ZIPs on this purchase email — not day-to-day Contractor Pro.',
  };
}

export function sampleDemoLabel(tier: SampleDemoTier): string {
  if (tier === 'free')
    return 'Free — bid-or-walk preview · next: Estimator $79 (Receipt the GC can file)';
  if (tier === 'partner')
    return 'Estimator — Receipt habit · next: Pro $149 (fee dollars · City Pack · CSV)';
  if (tier === 'pro')
    return 'Pro — bid desk · next: IC $1,500 (counsel ZIP — not a bigger City Pack)';
  return 'IC Diligence Bundle — counsel ZIP open · next: Annual $15,000 after about ~10 sites';
}
