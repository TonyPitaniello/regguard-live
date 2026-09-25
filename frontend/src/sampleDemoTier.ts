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

/** Sample / live-shaped next-step offer — Free→Estimator→Pro→IC */
export function sampleUpgradeOffer(tier: SampleDemoTier): NonNullable<AnalysisData['upgrade_offer']> {
  if (tier === 'free') {
    return {
      message: 'Unlock the next step — Estimator / Permit Runner',
      detail:
        'Free is a soft-locked preview. Estimator / Permit Runner ($79/mo) unlocks the full forwardable Bid Risk Receipt, the rest of the punch list, and Saved Jobs for client sites.',
      cta_label: 'Start Estimator / Permit Runner — $79/mo',
      cta_tier: 'partner',
      secondary_cta_label: 'See Contractor Pro — $149/mo',
      secondary_cta_tier: 'contractor_pro',
      current_label: 'Free Lookups',
      next_label: 'Estimator / Permit Runner — full Receipt + unlocked punch + Saved Jobs',
      primary_once: true,
      honesty_note: 'Climb one level at a time — IC Diligence Bundle is after Contractor Pro.',
    };
  }
  if (tier === 'partner') {
    return {
      message: 'Next level — Contractor Pro desk',
      detail:
        'Estimator unlocked Receipt + punch. Contractor Pro ($149/mo) adds Full City Pack, fee/punch CSV, bid packet, and deeper scout. IC Diligence Bundle is the step after Pro.',
      cta_label: 'Upgrade to Contractor Pro — $149/mo',
      cta_tier: 'contractor_pro',
      secondary_cta_label: undefined,
      secondary_cta_tier: undefined,
      current_label: 'Estimator / Permit Runner',
      next_label: 'Contractor Pro — City Pack · CSV · bid packet · deeper scout',
      primary_once: true,
      honesty_note: 'Pro adds desk formats — still confirm fees on the live AHJ schedule.',
    };
  }
  return {
    message: 'Next level — IC Diligence Bundle for this site',
    detail:
      'Pro unlocked the desk. IC Diligence Bundle ($1,500) ships the counsel ZIP: decision memo, boardroom PDF, counsel DOCX, estimator Excel, and evidence binder for this one address.',
    cta_label: 'Get IC Diligence Bundle — $1,500',
    cta_tier: 'ic_project',
    secondary_cta_label: 'Or IC Annual — $15,000/yr multi-site',
    secondary_cta_tier: 'ic_annual',
    current_label: 'Contractor Pro',
    next_label: 'IC Diligence Bundle — counsel ZIP + full scout for one site',
    primary_once: true,
    honesty_note: 'IC is counsel packaging for one site — not an AHJ filing.',
  };
}

export function sampleDemoLabel(tier: SampleDemoTier): string {
  if (tier === 'free') return 'Free Lookups — next: Estimator / Permit Runner ($79/mo)';
  if (tier === 'partner') return 'Estimator / Permit Runner — next: Contractor Pro ($149/mo)';
  return 'Contractor Pro — next: IC Diligence Bundle ($1,500)';
}
