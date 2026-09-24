/**
 * Canonical customer-facing product copy — estimator-first, IC-safe.
 * Import from here (or HABIT_TIERS / IC_BUNDLE) instead of inventing synonyms.
 */

import { HABIT_TIERS } from './habitDeliverableLadder';
import { IC_BUNDLE } from './icDiligenceBundleCopy';

/** Prose brand (sentences, SEO, disclaimers). Logo lockup may stay compact RegGuard. */
export const BRAND_PROSE = 'Reg Guard';

/** Compact wordmark for dense headers / logo text */
export const BRAND_LOCKUP = 'RegGuard';

export const PRODUCT_COPY = {
  brandProse: BRAND_PROSE,
  brandLockup: BRAND_LOCKUP,

  /** On-screen results panel after address entry */
  resultsPanelTitle: 'Site Diligence Results',

  /** Amber card at top of results */
  executiveSummary: 'Executive Summary',

  /** Forwardable one-pager / PDF habit artifact */
  bidRiskReceipt: 'Bid Risk Receipt',

  /** Full AHJ fee / gotcha pack */
  fullCityPack: 'Full City Pack',

  honestyShort: 'Planning aid only — not a quote or sealed bid.',
  honestyLong:
    'This is pre-bid research assistance, not a guarantee of fees, timelines, or AHJ approval. Confirm every item with the Authority Having Jurisdiction before you bid or file. Findings are labeled Source or Unverified.',

  /** Home hero */
  heroHeadline: 'Citeable Site Diligence Before You Bid',
  heroSubhead:
    'Enter a US address — get a forwardable Bid Risk Receipt. Source on every line, or an honest Unverified. No credit card to try it free.',
  seoTitle: 'Reg Guard — Bid Risk Receipt for Contractors',
  seoDescription:
    'Citeable pre-bid site diligence for US addresses — strongest in DFW and Austin. Forward a Bid Risk Receipt to your GC. Planning aid — not a quote or sealed bid.',

  sampleEyebrow: 'Labeled Sample',
  sampleLead: 'See What Reg Guard Can Do',
  sampleHeading: 'Sample Site Results',
  sampleBridge: 'Then run your own site below — same Bid Risk Receipt format.',

  formHeading: 'Now Run Your Site',
  formClear: 'Clear & Start Over',
  freeCta: 'Get My Bid Risk Receipt',
  paidCta: 'Run Deep Research on This Site',
  navTryFree: 'Try Free',

  progressGeocode: 'Finding the pin…',
  progressScreen: 'Checking permits & environment…',
  progressPunch: 'Building your Bid Risk Receipt…',

  freePreviewBadge: 'Free Preview — Citeable Fees & Top Punch Lines',
  freePreviewIncomplete: 'Free Preview — Not Full Pro Depth',

  /** Results panel section headings — Title Case throughout */
  sections: {
    flaggedBeforeBidDay: 'Flagged Before Bid Day',
    bidRiskReceiptForward: 'Bid Risk Receipt — Forward to GC / Owner',
    bidRiskReceiptShare: 'Bid Risk Receipt — Default Bid-File Forward',
    suggestedBidContingency: 'Suggested Bid Contingency',
    whatToResolve: 'What to Resolve Before Bid',
    immediatePunch: 'Immediate Punch Highlights',
    preBidPunchList: 'Pre-Bid Punch List',
    timeline: 'Timeline',
    estimatedCost: 'Estimated Cost',
    bidTimeDownloads: 'Bid-Time Downloads',
    feeTimelineExtract: 'Fee & Timeline Extract',
    localGotchaWatchlist: 'Local Gotcha Watchlist',
    inspectionSequence: 'Inspection Sequence',
    submitLocalGotcha: 'Submit a Local Gotcha',
    scoutBriefing: 'Scout Briefing',
    codeChangeWatchdog: 'Code-Change Watchdog',
    bottomLine: 'Bottom Line',
    environmentalFindings: 'Environmental Findings',
    verticalPlaybook: 'Vertical Playbook',
    coverage: 'Coverage',
  },

  homePriceStrip: {
    free: 'Free Bid Risk Receipt Preview',
    partner: HABIT_TIERS.partner.name,
    pro: HABIT_TIERS.contractor_pro.name,
    /** Quiet IC line — not the loudest home chip */
    icAlso: `Also: ${IC_BUNDLE.productName} — ${IC_BUNDLE.priceLabel}/site`,
  },

  stampLabels: {
    HOLD: 'HOLD',
    CAUTION: 'CAUTION',
    CLEAR: 'CLEAR',
  } as const,
} as const;

/** Display name for habit tier keys — never show "Partner" to customers */
export function habitTierDisplayName(tierKey: string): string {
  const k = (tierKey || '').toLowerCase();
  if (k === 'partner' || k === 'estimator' || k === 'permit_runner') {
    return HABIT_TIERS.partner.name;
  }
  if (k === 'contractor_pro' || k === 'pro') return HABIT_TIERS.contractor_pro.name;
  if (k === 'free' || k === 'free_preview') return HABIT_TIERS.free.name;
  if (k === 'ic' || k === 'ic_project' || k === 'ic_full') return IC_BUNDLE.tierName;
  if (k === 'ic_annual') return 'IC Annual';
  return tierKey || 'Plan';
}
