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

  honestyShort: 'Planning aid only — not a quote or sealed bid.',
  honestyLong:
    'This is pre-bid research assistance, not a guarantee of fees, timelines, or AHJ approval. Confirm every item with the Authority Having Jurisdiction before you bid or file. Findings are labeled Source or Unverified.',

  /** Home hero */
  heroHeadline: 'Citeable site diligence before you bid',
  heroSubhead:
    'Enter a US address — get a forwardable Bid Risk Receipt. Source on every line, or an honest Unverified. No credit card to try it free.',
  seoTitle: 'Reg Guard — Bid Risk Receipt for contractors',
  seoDescription:
    'Citeable pre-bid site diligence for US addresses — strongest in DFW and Austin. Forward a Bid Risk Receipt to your GC. Planning aid — not a quote or sealed bid.',

  sampleLead: 'See what Reg Guard can do',
  sampleHeading: 'Sample Site Results',
  sampleBridge: 'Then run your own site below — same Bid Risk Receipt format.',

  formHeading: 'Now Run Your Site',
  formClear: 'Clear & start over',
  freeCta: 'Get my Bid Risk Receipt',
  paidCta: 'Run deep research on this site',
  navTryFree: 'Try free',

  progressGeocode: 'Finding the pin…',
  progressScreen: 'Checking permits & environment…',
  progressPunch: 'Building your Bid Risk Receipt…',

  freePreviewBadge: 'Free preview — citeable fees & top punch lines',
  freePreviewIncomplete: 'Free preview — not full Pro depth',

  homePriceStrip: {
    free: 'Free Bid Risk Receipt preview',
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
