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
 *   - IC Annual ties at 10 sites ($15,000). The 11th site is where the year costs less.
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
      'In minutes: bid or walk — HOLD stamp, one permit sequence, every line Source or Unverified. The Receipt the GC can keep stays on Estimator. No card.',
    proof: 'Text the preview. Your GC sees HOLD and the top risks. The number they can file is on Estimator.',
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
      'Your client-site habit: full Bid Risk Receipt PDF, unlocked punch (owner · due · Source or Unverified), and Saved Jobs with reminders. The deepest packs are Dallas, Plano, Austin, and Fort Worth.',
    proof: 'One tap: forward the Receipt. Punch stays unlocked when you reopen the job.',
    vsBelow: 'Free proved bid-or-walk. Estimator makes it a weekly habit.',
    notThis: 'Not fee/punch CSV, not Full City Pack PDF, not deep scout every lookup, not counsel Word/Excel.',
    oneLiner:
      'Stop losing the thread with the GC — full forwardable Receipt + unlocked punch + Saved Jobs for client sites.',
    cta: 'Start Estimator / Permit Runner — $79/mo',
    upsellHeadline: 'Still opening the city portal before every bid?',
    upsellBody:
      'Estimator got you a Receipt the GC can file. Contractor Pro ($149/mo) adds paid local confirm, the City Pack PDF, a punch/fee CSV, and the bid packet. Fee dollars print only when a citeable pack or the official schedule states them.',
    upsellOffers: 'City Pack PDF · punch/fee CSV · bid packet · dollars only when stated',
    upsellCta: 'Upgrade to Contractor Pro — $149/mo',
  },

  pro: {
    key: 'pro',
    name: HABIT_TIERS.contractor_pro.name,
    price: `${HABIT_TIERS.contractor_pro.priceLabel}/mo`,
    who: 'Contractors who bid every week and own the number.',
    pain: 'One missed fee line or local gotcha blows the margin — and you burn hours chasing portals before every bid.',
    promise:
      'Your bid-week desk: everything in Estimator, plus paid local confirm, City Pack PDF, punch/fee CSV, and bid packet. Fee dollars print only when a citeable pack or the official page states them. A heavy day can hit the daily confirm cap — come back tomorrow rather than treating a capped run as a full desk.',
    proof: 'Download City Pack + CSV + packet beside the Receipt. Paste the lines the schedule actually stated.',
    vsBelow: 'Estimator forwards the stamp. Pro arms the estimate.',
    notThis:
      'Not a counsel ZIP. City Pack is the AHJ fee/gotcha desk — not the boardroom / Word / exhibit package counsel opens.',
    oneLiner: HABIT_TIERS.contractor_pro.oneLiner,
    cta: 'Start Contractor Pro — $149/mo',
    upsellHeadline: 'Counsel won’t mark up a City Pack PDF',
    upsellBody: IC_BUNDLE.deskAndZip,
    upsellOffers: 'Counsel ZIP: memo · boardroom · Word · Excel exhibits',
    upsellCta: 'Get IC Diligence Bundle — $1,500',
  },

  ic: {
    key: 'ic',
    name: IC_BUNDLE.tierName,
    price: IC_BUNDLE.priceLabel,
    who: 'IC consultants, owner’s reps, sponsors, and lenders screening one hard site.',
    pain: 'Counsel will not mark up a City Pack, and the day before the letter of intent is the one you cannot spend rebuilding the Word file.',
    promise:
      'One bound address → counsel-ready ZIP: HOLD/CLEAR memo, boardroom PDF, editable DOCX with live links, Fees/Punch/Evidence Excel, evidence index. Large-load sites add AHJ, utility interconnection, and water as separate clocks. Screening only — not an interconnection study.',
    proof: 'Attach the ZIP. Counsel redlines the DOCX. Exhibits map claim → EX-00N → URL.',
    vsBelow: 'Pro is the bid desk. IC is the counsel package for one site.',
    notThis:
      'Not a quote, sealed bid, interconnection study, geotech, or AHJ filing. Not “Pro with extra pages.”',
    oneLiner: IC_BUNDLE.oneLiner,
    cta: IC_BUNDLE.ctaBuy,
    upsellHeadline: 'Buying another Diligence Bundle for the next capital site?',
    upsellBody: IC_BUNDLE.annualMath,
    upsellOffers: 'Same counsel ZIP · new capital site · no new $1,500 PO',
    upsellCta: 'IC Annual — $15,000/yr',
  },

  ic_annual: {
    key: 'ic_annual',
    name: 'IC Annual',
    price: '$15,000/yr',
    who: 'IC consultants, owner’s reps, sponsors, and lenders packaging multiple capital sites a year.',
    pain: 'Every new capital address means another $1,500 Diligence Bundle — while the package shape never changes.',
    promise: IC_BUNDLE.annualMath,
    proof: 'Same memo · boardroom · DOCX · Excel — new bound address when the deal needs the package.',
    vsBelow: 'The Diligence Bundle proved the package. Annual covers more capital sites on the same purchase email.',
    notThis:
      'Daily lookups stay on Contractor Pro at $149 a month. Each site still needs its own three calls. A different purchase email still needs its own Diligence Bundle ($1,500).',
    oneLiner: IC_BUNDLE.annualMath,
    cta: 'Get IC Annual — $15,000/yr',
    upsellHeadline: 'Need the ZIP under a different purchase email?',
    upsellBody:
      'Annual covers Diligence Bundles for capital sites on this purchase email. For a different buyer email, buy the IC Diligence Bundle ($1,500) on that email — same counsel ZIP, separate purchase.',
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
