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
      'Electrical permit amounts are on the Jan 2, 2026 schedule (Ordinance 2025-11-4). Confirm the line for this job. $75 on that schedule is the first reinspection, not the permit total.',
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
      'Forward the receipt. The clear percent stays on Estimator ($79/mo)',
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
      'Next step is Estimator ($79/mo) for the clear percent. The $1,500 bundle is for one capital site, not this page',
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
      'Commercial building permit is 80% of the valuation table on the Oct 1, 2026 schedule. $300 is the application fee. $75 is the commercial reinspection, not the permit total.',
      'Do not copy a Plano fee line onto a Frisco bid',
      'Forward the receipt. Sharing the free page does not unlock the clear percent',
    ],
    feeNote: 'Confirm the bracket on the City of Frisco consolidated fee schedule before bid or filing.',
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
      'Remodel, finish-out, and addition permits follow the valuation table in the August 2023 fees summary. Re-inspection on that summary is $75. The summary\'s example does not match its table, so no permit total is stated here.',
      'Do not assume Austin Design Criteria',
      'Forwardable Bid Risk Receipt for the GC file',
    ],
    feeNote: 'Confirm the valuation bracket on the Round Rock Planning & Development Fees Summary before bid.',
  },
  {
    slug: 'arlington',
    city: 'Arlington',
    state: 'TX',
    title: 'Arlington TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for Arlington AHJ work',
    bullets: [
      'Commercial building permits and plan review follow the city fee schedule. Phase 2 took effect Oct 1, 2025. This page does not state a permit total.',
      'Source or Unverified on every punch line',
      'Planning aid — not a sealed bid',
    ],
    feeNote: 'Open the current Planning and Development Services fee schedule before you lock contingency. This page does not state a permit total.',
  },
  {
    slug: 'irving',
    city: 'Irving',
    state: 'TX',
    title: 'Irving TX permit fees & pre-bid gotchas',
    headline: 'Forwardable receipt for Irving AHJ work',
    bullets: [
      'Commercial building permit is $0.45 per square foot of the area of work, $1,200 minimum (Ordinances 2025-11146 and 2025-11165). Plan review is additional. That rate is not a permit total.',
      'Do not copy a Dallas or Plano fee line onto an Irving bid',
      'Forward the receipt. Sharing the free page does not unlock the clear percent',
    ],
    feeNote: 'Confirm the square footage and plan-review line on the City of Irving rates page before filing.',
  },
  {
    slug: 'garland',
    city: 'Garland',
    state: 'TX',
    title: 'Garland TX permit fees & pre-bid gotchas',
    headline: 'Pre-bid punch list for Garland sites',
    bullets: [
      'Commercial permit fee is a percent of valuation on the Building Permit page. Plan review is 40% of the permit fee, due at submittal, and Building Inspections permits carry a 4.5% technology surcharge. This page does not state a permit total.',
      'Source or Unverified labels',
      'Forward to GC before you submit the number',
    ],
    feeNote: 'Confirm the valuation bracket on the City of Garland Building Permit page before bid.',
  },
  {
    slug: 'mckinney',
    city: 'McKinney',
    state: 'TX',
    title: 'McKinney TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for McKinney AHJ work',
    bullets: [
      'Commercial permit fees are on the Permit Fees PDF linked from the city Fee Schedule page. This page does not state a permit total.',
      'Do not copy a Plano or Frisco fee line onto a McKinney bid',
      'Planning aid — confirm with the AHJ',
    ],
    feeNote: 'Open the Permit Fees PDF on the McKinney Fee Schedule page before filing. This page does not state a permit total.',
  },
  {
    slug: 'richardson',
    city: 'Richardson',
    state: 'TX',
    title: 'Richardson TX permit fees & pre-bid gotchas',
    headline: 'Forwardable Bid Risk Receipt for Richardson sites',
    bullets: [
      'The permit fee schedule is the PDF linked from Building Inspection forms. This page does not state a permit total.',
      'Source or Unverified on every line',
      'Forward the receipt to the GC. The clear percent stays on Estimator',
    ],
    feeNote: 'Open the permit fee schedule PDF on the Richardson Building Inspection forms page before bid or filing.',
  },
  {
    slug: 'carrollton',
    city: 'Carrollton',
    state: 'TX',
    title: 'Carrollton TX permit fees & pre-bid gotchas',
    headline: 'Pre-bid diligence for Carrollton AHJ work',
    bullets: [
      'New commercial work is $6 per $1,000 of value, $125 minimum, on the Building Inspection fees page. $125 is the application fee. $50 is the re-inspection, not the permit total.',
      'Do not use Plano or Dallas fee lines',
      'Not a quote — a Bid Risk Receipt',
    ],
    feeNote: 'Confirm the comprehensive fee schedule. The Building Inspection fees page says it is not the full schedule.',
  },
  {
    slug: 'houston',
    city: 'Houston',
    state: 'TX',
    title: 'Houston TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for City of Houston work',
    bullets: [
      'Commercial building permit follows the 2026 valuation table on the Houston Permitting Center schedule. Plan review is 25% of the estimated building permit fee and is non-refundable. This page does not state a permit total.',
      'Pasadena, Sugar Land, and The Woodlands are different schedules',
      'Next step is Estimator ($79/mo). Forwarding this page does not unlock the clear percent',
    ],
    feeNote: 'City of Houston only. Confirm the valuation bracket on the 2026 Houston Permitting Center schedule before bid.',
  },
  {
    slug: 'san-antonio',
    city: 'San Antonio',
    state: 'TX',
    title: 'San Antonio TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for San Antonio Development Services',
    bullets: [
      'Commercial plan review and permit fees follow the valuation tables in the FY 2027 Development Fee Schedule, revised October 2026. A 4% technology surcharge and a 4% Development Services surcharge apply unless a line says otherwise. This page does not state a permit total.',
      'Do not use the residential square-foot table on a commercial bid',
      'Next step is Estimator ($79/mo). The $1,500 bundle is for one capital site, not this page',
    ],
    feeNote: 'Confirm the valuation bracket on the FY 2027 Development Fee Schedule before bid. SAWS fees are a separate section.',
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
