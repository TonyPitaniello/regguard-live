/**
 * Canonical differentiation + upsell voice — Free → Estimator → Pro → IC.
 * Single source for Pricing, samples, results CTAs, depth_ladder parity.
 *
 * Pattern at every step (pain-first):
 *   WHO → PAIN → PROMISE → PROOF → NEXT (one step only)
 *
 * Premortem-hardened rules:
 *   - Free/Estimator: plain truck language (bid-or-walk), not jargon-first
 *   - Upsell body = who + pain of staying + one outcome — never a SKU dump
 *   - Never sell City Pack as counsel ZIP; never “more accurate”
 *   - IC Annual must show break-even (~10 sites) or it fails willingness
 *   - Upsell only to the *next* tier (Annual→Project = outside-seat exception)
 */

import { HABIT_TIERS } from './habitDeliverableLadder';
import { IC_BUNDLE } from './icDiligenceBundleCopy';

export type TierVoiceKey = 'free' | 'partner' | 'pro' | 'ic' | 'ic_annual';

export type TierVoice = {
  key: TierVoiceKey;
  name: string;
  price: string;
  who: string;
  pain: string;
  promise: string;
  proof: string;
  vsBelow: string;
  notThis: string;
  oneLiner: string;
  cta: string;
  upsellHeadline: string;
  upsellBody: string;
  upsellOffers: string;
  upsellCta: string;
};

export const TIER_VOICE: Record<TierVoiceKey, TierVoice> = {
  free: {
    key: 'free',
    name: HABIT_TIERS.free.name,
    price: HABIT_TIERS.free.priceLabel,
    who: 'Estimator or PM who wants a first look before burning a bid day.',
    pain: 'You’re about to price a site blind — and the landmines only show up after you’ve already spent the week.',
    promise:
      'In minutes: can you bid this address or walk — contingency band, top risks, every line marked Source or Unverified. No card.',
    proof: 'Preview you can text — top 5 risks, soft-locked until you unlock the full Receipt.',
    vsBelow: 'Entry proof — not a habit desk.',
    notThis: 'Not a full Receipt habit, not fee dollars, not City Pack PDF, not a counsel ZIP.',
    oneLiner:
      'First look before you burn a bid day — bid-or-walk preview, Source or Unverified. No card.',
    cta: 'Get My Free Bid-or-Walk Preview',
    upsellHeadline: 'Stop re-sending screenshots that fall apart in the GC thread',
    upsellBody:
      'You’re still on Free: shape of risk, nothing the GC can file. Estimator / Permit Runner ($79/mo) gives you the full Bid Risk Receipt you can forward, the rest of the punch list, and Saved Jobs — stamp every client site without rebuilding the story.',
    upsellOffers: 'Forwardable Receipt · full punch · Saved Jobs',
    upsellCta: 'Start Estimator / Permit Runner — $79/mo',
  },

  partner: {
    key: 'partner',
    name: HABIT_TIERS.partner.name,
    price: `${HABIT_TIERS.partner.priceLabel}/mo`,
    who: 'Permit runners and estimators screening client sites every week.',
    pain: 'The GC asks “send me something I can put in the bid file” — and all you’ve got is a chat dump and half a punch list.',
    promise:
      'Your client-site habit: full Bid Risk Receipt PDF, unlocked punch (owner · due · Source or Unverified), and Saved Jobs with reminders — strongest in DFW / Austin.',
    proof: 'One tap: forward the Receipt. Punch stays unlocked when you reopen the job.',
    vsBelow: 'Free proved bid-or-walk. Estimator makes it a weekly habit.',
    notThis: 'Not fee/punch CSV, not Full City Pack PDF, not deep scout every lookup, not counsel Word/Excel.',
    oneLiner:
      'Stop losing the thread with the GC — full forwardable Receipt + unlocked punch + Saved Jobs for client sites.',
    cta: 'Start Estimator / Permit Runner — $79/mo',
    upsellHeadline: 'Still hunting fee dollars and city schedules by hand?',
    upsellBody:
      'Estimator got you a Receipt the GC can file. You’re still the one scraping portals for fee lines before every bid. Contractor Pro ($149/mo) puts fee dollars, Full City Pack PDF, paste-ready CSV, and bid packet on the desk — for jobs where your number has to hold.',
    upsellOffers: 'Fee dollars on the schedule · City Pack PDF · CSV · bid packet',
    upsellCta: 'Upgrade to Contractor Pro — $149/mo',
  },

  pro: {
    key: 'pro',
    name: HABIT_TIERS.contractor_pro.name,
    price: `${HABIT_TIERS.contractor_pro.priceLabel}/mo`,
    who: 'Contractors who bid every week and own the number.',
    pain: 'One missed fee line or local gotcha blows the margin — and you burn hours chasing portals before every bid.',
    promise:
      'Your bid-week desk: everything in Estimator, plus paid local confirm / light scout, fee dollars, Full City Pack PDF, fee/punch CSV, and bid packet on every lookup.',
    proof: 'Download City Pack + CSV + packet beside the Receipt — paste into the estimate the same day.',
    vsBelow: 'Estimator forwards the stamp. Pro arms the estimate.',
    notThis:
      'Not a counsel ZIP. City Pack is the AHJ fee/gotcha desk — not the boardroom / Word / exhibit package counsel opens.',
    oneLiner:
      'Bid-week desk if you own the number — City Pack, fee CSV, bid packet. One missed fee line pays for the month.',
    cta: 'Start Contractor Pro — $149/mo',
    upsellHeadline: 'Counsel won’t mark up a City Pack PDF',
    upsellBody:
      'Pro is the bid desk. For one capital-sensitive address — LOI, IC call, owner’s rep, lender — IC Diligence Bundle ($1,500) ships the counsel ZIP: decision memo, boardroom brief, editable Word with exhibits, Excel evidence map. Same AHJ facts in counsel format — not a bigger City Pack.',
    upsellOffers: 'Counsel ZIP: memo · boardroom · Word · Excel exhibits',
    upsellCta: 'Get IC Diligence Bundle — $1,500',
  },

  ic: {
    key: 'ic',
    name: IC_BUNDLE.tierName,
    price: IC_BUNDLE.priceLabel,
    who: 'IC consultants, owner’s reps, sponsors, and lenders screening one hard site.',
    pain: 'Screenshots get rejected. The LOI / IC call needs a package with exhibits — and you don’t have half a day to build Word and Excel by hand.',
    promise:
      'One bound address → counsel-ready ZIP: HOLD/CLEAR memo, boardroom PDF, editable DOCX with live links, Fees/Punch/Evidence Excel, evidence index — with fuller Universal Scout when the site needs it (including DC parallel clocks).',
    proof: 'Attach the ZIP. Counsel redlines the DOCX. Exhibits map claim → EX-00N → URL.',
    vsBelow: 'Pro is the bid desk. IC is the counsel package for one site.',
    notThis:
      'Not a quote, sealed bid, interconnection study, geotech, or AHJ filing. Not “Pro with extra pages.”',
    oneLiner:
      'The package counsel and lenders open — memo, boardroom, editable Word with exhibits, Excel evidence — for one capital site. Not a bigger City Pack.',
    cta: IC_BUNDLE.ctaBuy,
    upsellHeadline: 'Still cutting a $1,500 PO every time a new address hits the pipeline?',
    upsellBody:
      'IC Project is one bound site. IC Annual ($15,000/yr) is shop rate for Diligence Bundle ZIPs across your pipeline — break-even around the 10th site. Fair use: ~25 fresh Pro scrapes/day; Generate IC still builds the counsel ZIP.',
    upsellOffers: 'Counsel ZIPs across sites · ~10× break-even · fair use ~25 scrapes/day',
    upsellCta: 'IC Annual — $15,000/yr',
  },

  ic_annual: {
    key: 'ic_annual',
    name: 'IC Annual',
    price: '$15,000/yr',
    who: 'IC / diligence shops packaging many capital sites a year.',
    pain: 'Your pipeline is a stack of LOIs — and finance still treats every address like a one-off $1,500 PO.',
    promise:
      'One Annual seat → Diligence Bundle ZIP for each new bound address (no per-site $1,500). Break-even ~10 sites. Fair use: ~25 fresh Pro scrapes/day; Generate IC still builds the counsel package.',
    proof: 'Same memo · boardroom · DOCX · Excel — new address each time. ~10 sites covers the year vs Project rate.',
    vsBelow: 'IC Project proved the package. Annual scales the shop.',
    notThis:
      'Not a firehose of uncapped Pro scrapes. Not a substitute for AHJ confirm. Outside-seat one-offs still need a $1,500 Project.',
    oneLiner:
      'Counsel ZIPs across your pipeline — ~10 sites breaks even vs $1,500/Project. Fair use ~25 fresh scrapes/day.',
    cta: 'Get IC Annual — $15,000/yr',
    upsellHeadline: 'Need a one-off address outside your Annual seat?',
    upsellBody:
      'Annual covers Diligence Bundle regenerations under your shop seat. For a bound address outside that seat, buy another IC Project ($1,500) — same counsel ZIP, separate PO.',
    upsellOffers: 'One more bound-address counsel ZIP — $1,500',
    upsellCta: 'IC Diligence Bundle for another site — $1,500',
  },
} as const;

export function voiceForLadderTier(tier: 'free' | 'partner' | 'pro' | 'ic'): TierVoice {
  if (tier === 'partner') return TIER_VOICE.partner;
  if (tier === 'pro') return TIER_VOICE.pro;
  if (tier === 'ic') return TIER_VOICE.ic;
  return TIER_VOICE.free;
}

export function nextVoiceForLadderTier(
  tier: 'free' | 'partner' | 'pro' | 'ic',
  opts?: { ownsIcAnnual?: boolean }
): TierVoice {
  if (tier === 'free') return TIER_VOICE.partner;
  if (tier === 'partner') return TIER_VOICE.pro;
  if (tier === 'pro') return TIER_VOICE.ic;
  if (opts?.ownsIcAnnual) return TIER_VOICE.ic;
  return TIER_VOICE.ic_annual;
}
