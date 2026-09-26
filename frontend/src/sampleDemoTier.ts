/**
 * Sample ladder demos — Free (least + blur) → Estimator (more) → Pro (full Pro desk).
 * Applied on /sample-site-diligence?tier=…
 */

import type { AnalysisData } from './ResultsViewerModal';

export type SampleDemoTier = 'free' | 'partner' | 'pro';

export const SAMPLE_DEMO_PUNCH_VISIBLE: Record<SampleDemoTier, number> = {
  free: 5,
  partner: 99,
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
    // Free: keep stamp + thin env headline, hide Pro playbook / pro_delta
    delete clone.vertical_playbook;
    delete clone.pro_delta;
    if (clone.environmental_screening?.findings) {
      clone.environmental_screening = {
        ...clone.environmental_screening,
        findings: clone.environmental_screening.findings.slice(0, 2),
      };
    }
  } else if (tier === 'partner') {
    clone.depth_tier = 'partner';
    clone.research_depth = 'partner';
    clone.depth_badge = 'SAMPLE — Estimator / Permit Runner';
    clone.ic_package = false;
    clone.research_incomplete = false;
    clone.depth_claim_honest = true;
    clone.scout_mode = 'none';
    // Estimator: env + receipt unlocked; Pro playbook still teaser-level
    delete clone.pro_delta;
    if (clone.vertical_playbook?.items) {
      clone.vertical_playbook = {
        ...clone.vertical_playbook,
        items: clone.vertical_playbook.items.slice(0, 3),
        stats: { completeness_pct: 38, cited: 2, confirm: 1 },
      };
    }
  } else {
    clone.depth_tier = 'pro_light';
    clone.research_depth = 'pro';
    clone.depth_badge = 'SAMPLE — Contractor Pro — Local Confirm + Light Scout';
    clone.ic_package = false;
    clone.research_incomplete = false;
    clone.depth_claim_honest = true;
    clone.scout_mode = 'light';
    // Full env + zoning playbook + Pro delta stay on the clone from the fixture
  }

  clone.research_id = `rg-sample-chapin-${tier}`;
  clone.sample_demo_tier = tier;
  const access =
    tier === 'pro' ? 'contractor_pro' : tier === 'partner' ? 'partner' : 'free';
  (clone as AnalysisData & { access_tier?: string }).access_tier = access;
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
  return {
    message: 'Counsel won’t mark up a City Pack PDF',
    detail:
      'Pro is the bid desk. For one capital-sensitive address — LOI, IC call, owner’s rep, lender — IC Diligence Bundle ($1,500) ships the counsel ZIP: memo, boardroom, Word with exhibits, Excel evidence. Not a bigger City Pack.',
    cta_label: 'Get IC Diligence Bundle — $1,500',
    cta_tier: 'ic_project',
    secondary_cta_label: 'Or IC Annual — $15,000/yr shop rate',
    secondary_cta_tier: 'ic_annual',
    current_label: 'Contractor Pro',
    next_label: 'Counsel ZIP — memo · boardroom · Word · Excel exhibits',
    primary_once: true,
    honesty_note: 'IC is counsel packaging for one site — not an AHJ filing.',
  };
}

export function sampleDemoLabel(tier: SampleDemoTier): string {
  if (tier === 'free')
    return 'Free — bid-or-walk preview · next: Estimator $79 (Receipt the GC can file)';
  if (tier === 'partner')
    return 'Estimator — Receipt habit · next: Pro $149 (fee dollars · City Pack · CSV)';
  return 'Pro — bid desk · next: IC $1,500 (counsel ZIP — not a bigger City Pack)';
}
