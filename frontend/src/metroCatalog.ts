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
      'Electrical permit amounts are on the Jan 2, 2026 schedule (Ordinance 2025-11-4). $75 on that schedule is the first reinspection, not the permit total.',
      'Every line is Source or Unverified — forward only what you can defend',
    ],
    feeNote:
      'Ordinance 2025-11-4 states the floor-area inspection lines and the $75 first reinspection. No single electrical total is stated for a multi-building campus.',
    samplePdf: true,
  },
  {
    slug: 'dallas',
    city: 'Dallas',
    state: 'TX',
    title: 'Dallas TX permit fees & pre-bid gotchas',
    headline: 'Bid-day CYA for Dallas commercial / industrial bids',
    bullets: [
      'DallasNow record type is Commercial New Construction or an alteration.',
      'The July 1, 2025 fee summary states $175 and $125. It does not state a new-construction permit total.',
      'Forward the receipt. The punch the GC can keep stays on Estimator ($79/mo). No schedule states a contingency percent for this address.',
    ],
    feeNote: 'The July 1, 2025 fee summary states $175 and $125. It does not state a new-construction permit total.',
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
      'Next step is Estimator ($79/mo) for the Receipt the GC can keep. The $1,500 bundle is for one capital site, not this page',
    ],
    feeNote:
      'The commercial fee schedule states the bases. It does not state a permit total without an official building area.',
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
      'Forward the receipt. Sharing the free page does not unlock the punch',
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
      'The building permit is issued before a trade permit can be applied for.',
      'Source or Unverified on every line',
      'Forward the receipt to your GC — planning aid, not a quote',
    ],
    feeNote: 'Ordinance 26-28781 states the Table 1-B deposits. Those lines are not a permit total, and they are not added together.',
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
    feeNote: 'The permit follows the valuation bracket on the Round Rock Planning & Development Fees Summary. This page does not state a permit total.',
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
      'Forward the receipt. Sharing the free page does not unlock the punch',
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
    feeNote: 'The permit follows the valuation bracket on the City of Garland Building Permit page. This page does not state a permit total.',
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
      'Planning aid. Not a quote, a permit total, or a filing.',
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
      'Forward the receipt to the GC. The punch the GC can keep stays on Estimator',
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
      'Next step is Estimator ($79/mo). Forwarding this page does not unlock the punch',
    ],
    feeNote: 'City of Houston only. The permit follows the valuation bracket on the 2026 Houston Permitting Center schedule. This page does not state a permit total.',
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
    feeNote: 'The commercial permit follows the valuation tables in the FY 2027 Development Fee Schedule. This page does not state a permit total. SAWS fees are a separate section.',
  },
  {
    slug: 'phoenix',
    city: 'Phoenix',
    state: 'AZ',
    title: 'Phoenix AZ permit fees & pre-bid gotchas',
    headline: 'Bid-day sheet for Phoenix Planning & Development',
    bullets: [
      'Ordinance G-7465, effective January 20, 2026, prices the building permit from Table A.',
      'Re-inspection is $195 each in the cases the schedule names. Temporary certificate of occupancy is $780 per request.',
      'A Table A bracket is not the permit total.',
    ],
    feeNote: 'The building permit follows Table A. $195 is the re-inspection. $780 is the temporary certificate of occupancy. This page does not state a permit total.',
  },
  {
    slug: 'mesa',
    city: 'Mesa',
    state: 'AZ',
    title: 'Mesa AZ permit fees & pre-bid gotchas',
    headline: 'Bid-day sheet for Mesa Development Services',
    bullets: [
      'The July 2026 Development Services schedule prices the commercial permit from the valuation table.',
      'Factory-built site review is $263 per unit. The civil engineering deposit is $390 per sheet.',
      'The four percent technology fee is not added on this page.',
    ],
    feeNote: 'The commercial permit follows the valuation table. $263 and $390 are the stated flat lines. This page does not state a permit total.',
  },
  {
    slug: 'atlanta',
    city: 'Atlanta',
    state: 'GA',
    title: 'Atlanta GA permit fees & pre-bid gotchas',
    headline: 'Bid-day sheet for Atlanta City Planning',
    bullets: [
      'The building permit is $7 per $1,000 of cost of construction, with a $150 minimum.',
      'The technology fee is $25 per permit. Commercial demolition is $1,860 each.',
      'The rate is not printed as a permit total.',
    ],
    feeNote: 'The building permit stays on the $7 per $1,000 row. $150 is the minimum. $25 is the technology fee. This page does not state a permit total.',
  },
  {
    slug: 'loudoun-county',
    city: 'Loudoun County',
    state: 'VA',
    title: 'Loudoun County VA permit fees & pre-bid gotchas',
    headline: 'Bid-day sheet for Loudoun County Building and Development',
    bullets: [
      'The fee schedule effective July 1, 2022 prices a new building from the valuation formula.',
      'The minimum permit fee is $65. Re-inspection is $65. The commercial occupancy permit is $70.',
    ],
    feeNote: 'The new-building permit stays on the valuation formula. $65 is the minimum and the re-inspection. $70 is the commercial occupancy permit.',
  },
  {
    slug: 'prince-william-county',
    city: 'Prince William County',
    state: 'VA',
    title: 'Prince William County VA permit fees & pre-bid gotchas',
    headline: 'Bid-day sheet for Prince William County Building Development',
    bullets: [
      'The fee schedule effective July 1, 2026 prices new nonresidential construction per square foot.',
      'The minimum fee per structure or tenant space is $368.45, the total the table states.',
    ],
    feeNote: 'The permit stays on the per-square-foot row. $368.45 is the stated minimum per structure or tenant space.',
  },
  {
    slug: 'new-albany',
    city: 'New Albany',
    state: 'OH',
    title: 'New Albany OH permit fees & pre-bid gotchas',
    headline: 'Bid-day sheet for New Albany Community Development',
    bullets: [
      'The commercial new-building structure base fee is $250. Occupancy is $75. Zoning is $30.',
      'The inspection fee is per square foot. The 3 percent state fee is not added on this page.',
    ],
    feeNote: 'The inspection stays on the per-square-foot line. $250, $75, and $30 are the stated flat lines. This page does not state a permit total.',
  },
  {
    slug: 'columbus',
    city: 'Columbus',
    state: 'OH',
    title: 'Columbus OH permit fees & pre-bid gotchas',
    headline: 'Bid-day sheet for Columbus Building and Zoning Services',
    bullets: [
      'The 2026 schedule prices commercial new construction as a base plus an amount for each 10 gross square feet over 1,000.',
      'A single-inspection permit is $550. An additional inspection trip is $225.',
    ],
    feeNote: 'The new-construction permit stays on the area line. $550 is the single-inspection permit. This page does not state a permit total.',
  },
  {
    slug: 'hillsboro',
    city: 'Hillsboro',
    state: 'OR',
    title: 'Hillsboro OR permit fees & pre-bid gotchas',
    headline: 'Bid-day sheet for the Hillsboro Building Division',
    bullets: [
      'Building permits follow the valuation table.',
      'Reinspection under Section 108.8 is $64.90. The temporary certificate of occupancy is $150.',
    ],
    feeNote: 'The building permit stays on the valuation table. $64.90 is the reinspection. $150 is the temporary certificate of occupancy.',
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
