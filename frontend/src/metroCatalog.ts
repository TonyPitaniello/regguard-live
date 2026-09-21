/** Beachhead metros — keep slugs in sync with backend city_packs / passive_campaign. */

export type MetroLanding = {
  slug: string;
  city: string;
  state: string;
  title: string;
  headline: string;
  bullets: string[];
  feeNote: string;
  samplePdf?: boolean;
};

export const METRO_LANDINGS: MetroLanding[] = [
  {
    slug: 'plano',
    city: 'Plano',
    state: 'TX',
    title: 'Plano TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for Plano AHJ work — not a code encyclopedia',
    bullets: [
      'Plano Ord. 250.50 grounding (dual 8-ft rods @ 20 ft, 2/0 bond) when citeable',
      '2026 electrical permit fee sync noted as $75 total — confirm on City of Plano schedule',
      'Every line is Source or Unverified — forward only what you can defend',
    ],
    feeNote:
      'Fee figures are planning aids. Always confirm with City of Plano Building Inspections before bid or filing.',
    samplePdf: true,
  },
  {
    slug: 'dallas',
    city: 'Dallas',
    state: 'TX',
    title: 'Dallas TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for Dallas commercial / industrial bids',
    bullets: [
      'Confirm trade permit type early — wrong path stalls review',
      'Fee schedule is not a fixed number — recheck before bid',
      'ERCOT / TDSP large-load clocks run parallel to city permits',
    ],
    feeNote: 'Dallas fees and amendments change. Confirm with Dallas Building Inspection before filing.',
  },
  {
    slug: 'austin',
    city: 'Austin',
    state: 'TX',
    title: 'Austin TX permit fees & pre-bid gotchas',
    headline: 'Pre-bid punch list for Austin Design Criteria risks',
    bullets: [
      'Austin gas-relief clearance and service-upgrade patterns when citeable',
      'Source or Unverified on every punch line',
      'IC Diligence Bundle adds memo + counsel DOCX + fee/punch CSV + evidence (not official filings)',
    ],
    feeNote:
      'Austin Development Services fees and Design Criteria override generic NEC narratives — verify before bid.',
  },
  {
    slug: 'frisco',
    city: 'Frisco',
    state: 'TX',
    title: 'Frisco TX permit fees & pre-bid gotchas',
    headline: 'Forwardable Bid Risk Receipt for Frisco AHJ work',
    bullets: [
      'Screen Frisco permit path before you price the job',
      'Citeable punch list when sources exist',
      'Share to unlock the full free preview — upgrade for deep scout',
    ],
    feeNote: 'Confirm fees with Frisco Development Services before bid or filing.',
  },
  {
    slug: 'fort-worth',
    city: 'Fort Worth',
    state: 'TX',
    title: 'Fort Worth TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for Fort Worth AHJ work',
    bullets: [
      'Confirm trade application type and inspection wait before bid',
      'Source or Unverified on every line',
      'Forward the receipt to your GC — planning aid, not a quote',
    ],
    feeNote: 'Confirm fees with City of Fort Worth Development Services before filing.',
  },
  {
    slug: 'round-rock',
    city: 'Round Rock',
    state: 'TX',
    title: 'Round Rock TX permit fees & pre-bid gotchas',
    headline: 'Pre-bid diligence for Round Rock sites',
    bullets: [
      'Screen AHJ risks before you price the job',
      'City gotchas called out when citeable',
      'Forwardable Bid Risk Receipt for the GC file',
    ],
    feeNote: 'Confirm fees with Round Rock Planning & Development Services before bid.',
  },
  {
    slug: 'arlington',
    city: 'Arlington',
    state: 'TX',
    title: 'Arlington TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for Arlington AHJ work',
    bullets: [
      'Confirm permit path and inspection timing',
      'Source or Unverified on every punch line',
      'Planning aid — not a sealed bid',
    ],
    feeNote: 'Confirm fees with City of Arlington before you lock contingency.',
  },
  {
    slug: 'irving',
    city: 'Irving',
    state: 'TX',
    title: 'Irving TX permit fees & pre-bid gotchas',
    headline: 'Forwardable receipt for Irving AHJ work',
    bullets: [
      'Screen Irving permit risks before bid day',
      'Citeable lines when official sources exist',
      'Share the /r/ link — that is the sales force',
    ],
    feeNote: 'Confirm fees with City of Irving before filing.',
  },
  {
    slug: 'garland',
    city: 'Garland',
    state: 'TX',
    title: 'Garland TX permit fees & pre-bid gotchas',
    headline: 'Pre-bid punch list for Garland sites',
    bullets: [
      'AHJ path and fee-type clarity (permit vs connection)',
      'Source or Unverified labels',
      'Forward to GC before you submit the number',
    ],
    feeNote: 'Confirm fees with City of Garland Building Inspection before bid.',
  },
  {
    slug: 'mckinney',
    city: 'McKinney',
    state: 'TX',
    title: 'McKinney TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for McKinney AHJ work',
    bullets: [
      'Confirm trade permit type early',
      'City gotchas when citeable',
      'Planning aid — confirm with the AHJ',
    ],
    feeNote: 'Confirm fees with McKinney Development Services before filing.',
  },
  {
    slug: 'richardson',
    city: 'Richardson',
    state: 'TX',
    title: 'Richardson TX permit fees & pre-bid gotchas',
    headline: 'Forwardable Bid Risk Receipt for Richardson sites',
    bullets: [
      'Screen permit and inspection timing before you price',
      'Source or Unverified on every line',
      'Share to unlock the full free preview',
    ],
    feeNote: 'Confirm fees with City of Richardson before bid or filing.',
  },
  {
    slug: 'carrollton',
    city: 'Carrollton',
    state: 'TX',
    title: 'Carrollton TX permit fees & pre-bid gotchas',
    headline: 'Pre-bid diligence for Carrollton AHJ work',
    bullets: [
      'Confirm application type and fee path',
      'Citeable punch list when sources exist',
      'Not a quote — a Bid Risk Receipt',
    ],
    feeNote: 'Confirm fees with City of Carrollton before you lock contingency.',
  },
];

export function metroFromPath(pathname: string): MetroLanding | undefined {
  const p = (pathname || '').toLowerCase();
  if (p === '/permit-fees' || p === '/permit-fees/') return undefined;
  const m = p.match(/^\/([a-z0-9-]+)-permit-fees\/?$/);
  const slug = m?.[1];
  if (!slug) return undefined;
  return METRO_LANDINGS.find((x) => x.slug === slug);
}

export function isMetroPermitPath(pathname: string): boolean {
  return Boolean(metroFromPath(pathname)) || pathname.replace(/\/$/, '') === '/permit-fees';
}
