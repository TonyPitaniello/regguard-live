/**
 * Sample ladder demos — Free (least + blur) → Estimator (more) → Pro (full Pro desk).
 * Applied on /sample-site-diligence?tier=…
 */

import type { AnalysisData } from './ResultsViewerModal';

export type SampleDemoTier = 'free' | 'partner' | 'pro';

export const SAMPLE_DEMO_PUNCH_VISIBLE: Record<SampleDemoTier, number> = {
  free: 3,
  partner: 8,
  pro: 99,
};

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
] as const;

export function parseSampleDemoTier(raw: string | null | undefined): SampleDemoTier | null {
  const t = String(raw || '').toLowerCase().trim();
  if (t === 'free' || t === 'partner' || t === 'pro') return t;
  if (t === 'estimator' || t === 'permit' || t === 'permit_runner') return 'partner';
  if (t === 'contractor_pro' || t === 'contractor-pro') return 'pro';
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

  if (tier === 'free') {
    clone.depth_tier = 'free';
    clone.research_depth = 'free';
    clone.depth_badge = 'SAMPLE — Free Lookups preview';
    clone.ic_package = false;
    clone.research_incomplete = false;
    clone.depth_claim_honest = true;
  } else if (tier === 'partner') {
    clone.depth_tier = 'partner';
    clone.research_depth = 'partner';
    clone.depth_badge = 'SAMPLE — Estimator / Permit Runner';
    clone.ic_package = false;
    clone.research_incomplete = false;
    clone.depth_claim_honest = true;
  } else {
    clone.depth_tier = 'pro_local';
    clone.research_depth = 'pro';
    clone.depth_badge = 'SAMPLE — Contractor Pro desk';
    clone.ic_package = false;
    clone.research_incomplete = false;
    clone.depth_claim_honest = true;
  }

  clone.research_id = `rg-sample-chapin-${tier}`;
  clone.sample_demo_tier = tier;
  return clone;
}

export function sampleDemoLabel(tier: SampleDemoTier): string {
  if (tier === 'free') return 'Free Lookups — least shown · locked lines blurred';
  if (tier === 'partner') return 'Estimator / Permit Runner — more unlocked · Pro desk still locked';
  return 'Contractor Pro — full Pro desk unlocked (IC Bundle still separate)';
}
