/**
 * Canonical marketing copy for the $1,500 IC Diligence Bundle.
 * Single source of truth for Pricing / Checkout / Results / Methodology.
 *
 * Pricing promise (must match the Bundle ZIP exactly):
 *   01 Decision memo PDF
 *   02 Boardroom PDF (full brief)
 *   03 Counsel DOCX (editable same brief + hyperlinks)
 *   04 Fee / punch / evidence Excel (Fees · Punch · Evidence sheets)
 *   05 Evidence index Excel (Exhibits · Claims · Index)
 *   06–07 Optional CSV paste exports
 *   Parallel clocks live in the boardroom PDF and counsel DOCX
 */

export const IC_BUNDLE = {
  productName: 'IC Diligence Bundle',
  /** Same product name on cards / samples — “IC Project” is the checkout SKU key only */
  tierName: 'IC Diligence Bundle',
  priceLabel: '$1,500',
  billing: 'one-time per site',
  segment: 'IC · Owner’s Rep · Sponsor · Lender',

  /** Short badge / nav / price strip */
  badge: 'Counsel-ready ZIP for one site',

  /** Hero / card one-liner — keep in lockstep with Pricing pitch */
  oneLiner:
    'The package counsel and lenders open — memo, boardroom, editable Word with exhibits, Excel evidence — for one capital site. Not a bigger City Pack.',

  /** Slightly shorter for dense cards / IC Project tier card */
  cardDescription:
    'Counsel-ready ZIP for one site — decision memo, boardroom PDF, editable DOCX with evidence binder, estimator Excel (Fees · Punch · Evidence), optional CSVs, and parallel clocks when it matters. Not a bigger City Pack. Not a quote, sealed bid, interconnection study, geotech, or AHJ filing.',

  /** Emotional draw — why buy */
  whyBuy:
    'Counsel won’t mark up a City Pack PDF. Walk into the LOI / IC call with a citeable ZIP: HOLD or CLEAR, why contingency exists, which exhibit backs each claim, and which clocks can slip independently — without spending half a day building Word and Excel by hand.',

  /** Who it’s for */
  forWhom:
    'Built for IC consultants, owner’s reps, sponsors, and lenders screening commercial–industrial and data-center-adjacent sites — especially Dallas · Plano · Fort Worth · Austin.',

  /**
   * What’s in the ZIP — benefit-led.
   * File labels must match ic_diligence_bundle.py archive members exactly
   * (except “Inside PDF / DOCX” which is content inside those files).
   *
   * Contract (shipped ZIP members):
   *   01_DECISION_MEMO.pdf
   *   02_IC_DILIGENCE_BOARDROOM.pdf
   *   03_IC_DILIGENCE_COUNSEL.docx
   *   04_FEE_PUNCH_EVIDENCE.xlsx
   *   05_EVIDENCE_INDEX.xlsx
   *   optional/FEE_PUNCH_SCHEDULE.csv
   *   optional/EVIDENCE_INDEX.csv
   */
  contents: [
    {
      file: '01 · Decision memo PDF',
      label: '1-page HOLD / CLEAR stamp',
      detail:
        'Bid Risk Receipt: contingency band, top 3 drivers, Source or Unverified — the artifact you forward in one tap.',
    },
    {
      file: '02 · Boardroom PDF',
      label: 'Full boardroom brief',
      detail:
        'Stamp, contingency, parallel clocks, AHJ/fees/gotchas, full punch list, evidence binder (EX-00N), and source appendix — the diligence document you attach or print.',
    },
    {
      file: '03 · Counsel DOCX',
      label: 'Editable Word for redlines',
      detail:
        'Same boardroom brief with live hyperlinks, evidence binder (EX-001…), claim map, and parallel clocks counsel can mark up.',
    },
    {
      file: '04 · Fee / punch / evidence Excel',
      label: 'Estimator-ready workbook',
      detail:
        'Cover + Fees · Punch · Evidence — trade, owner, due window, exhibit IDs, live source hyperlinks. Built for the Excel desk estimators already use.',
    },
    {
      file: '05 · Evidence index Excel',
      label: 'Numbered exhibit map',
      detail:
        'Cover + Exhibits · Claims · Index. Every cited claim → exhibit ID → source URL. No orphan screenshots.',
    },
    {
      file: 'optional/ · CSV paste exports',
      label: 'Optional Sheets paste',
      detail:
        'Same fee/punch + evidence data as CSV inside optional/ — for Google Sheets or model paste. Primary deliverables are the Excel workbooks.',
    },
    {
      file: 'Inside boardroom PDF + counsel DOCX',
      label: 'DC parallel clocks',
      detail:
        'AHJ permits · utility interconnect · water / NPDES as independent tracks — so schedule risk isn’t collapsed into one fake date.',
    },
  ] as const,

  /** Bullet list for pricing / checkout feature arrays */
  featureBullets: [
    'ZIP download: decision memo + boardroom PDF + counsel DOCX + Excel workbooks + optional CSVs',
    '1-page HOLD/CLEAR decision memo (Bid Risk Receipt) — forwardable stamp',
    'Full boardroom PDF — punch list, exhibits, parallel clocks',
    'Editable counsel DOCX with live source hyperlinks + evidence binder (EX-00N)',
    'Estimator Excel: Fees · Punch · Evidence sheets (trade · owner · due window · exhibit_id)',
    'Evidence index Excel: Exhibits · Claims · Index — every claim mapped to a numbered exhibit',
    'Optional CSV paste exports of the same schedule + evidence index',
    'Data-center parallel clocks: AHJ · interconnect · water/NPDES',
    'Strongest citeable coverage today: Dallas / Plano / Austin TX',
  ] as const,

  /**
   * Annual — sell firm volume on capital sites; soft-gate overuse without jargon.
   * Premortem-hardened:
   *   - No “Pro spray” / “shop rate” / “outside-seat” jargon
   *   - ~10 is break-even math (when Annual wins), not a purchase minimum
   *   - Speak to IC / owner’s rep / lender who *are* the diligence seat — not only “brief counsel”
   */
  annualDescription:
    'If you package Diligence Bundles for capital sites all year, stop rebuying at $1,500 each. After your first IC Project, IC Annual ($15,000/yr) covers the same counsel ZIP for more bound addresses on this purchase email — ahead of Project rate once you pass about ~10 sites.',
  annualFeatures: [
    'Same Diligence Bundle ZIP for each new bound capital site on this purchase email',
    'Memo · boardroom PDF · counsel Word · Excel exhibits — every address',
    'Ahead of $1,500/Project once you pass ~10 sites in a year',
    'For deal-ready IC / lender packages — not day-to-day Contractor Pro lookups',
    'Strongest citeable coverage: Dallas / Plano / Austin TX',
    'Email support via support@regguardagent.com',
  ] as const,
  /** Results / capped-scrape — quality pace; no scrape counter, no firehose invite */
  annualFairUseNote:
    'Annual covers Diligence Bundles for capital sites on this purchase email. Fresh scrapes pace for quality; Generate IC when this address needs the ZIP.',
  /** Wrong-depth body when buyer already has Annual */
  generateBodyAnnual:
    'This run is still free / Pro depth. Re-run with Generate IC to unlock the counsel ZIP for this address under your Annual. Same Diligence Bundle — memo · boardroom · Word · Excel.',

  /** CTAs */
  ctaBuy: 'Get IC Diligence Bundle — $1,500',
  ctaOrder: 'Order IC Diligence Bundle',
  ctaDownload: 'Download IC Diligence Bundle (ZIP)',
  ctaUnlock: 'Unlock IC Diligence Bundle',
  ctaGenerate: 'Generate IC Diligence Bundle for this site',

  /** Results — paid ready */
  readyHeadline: 'Your IC Diligence Bundle is ready',
  readyBody:
    'Primary $1,500 deliverable: one ZIP with the decision memo, full boardroom PDF, counsel DOCX (evidence binder + hyperlinks), estimator Excel (Fees · Punch · Evidence), evidence index Excel, and optional CSV paste exports. Parallel clocks are in the boardroom PDF and DOCX. Download individual parts below if you only need one file.',

  /** Results — owns IC but wrong depth */
  generateHeadline: 'Generate the Diligence Bundle for this paid site',
  generateBody:
    'This run is still free / Pro depth. Re-run with Generate IC Report to unlock the counsel ZIP for this address: memo + boardroom PDF + DOCX + Excel. A different address needs a new $1,500 IC Project purchase.',

  /** Results — Pro upsell */
  upsellHeadline: 'Counsel won’t mark up a City Pack PDF',
  upsellBody:
    'Pro is the bid desk. For one capital-sensitive address — LOI, IC call, owner’s rep, lender — IC Diligence Bundle ($1,500) ships the counsel ZIP: decision memo, boardroom brief, editable Word with exhibits, Excel evidence map. Same AHJ facts in counsel format — not a bigger City Pack.',

  /** Results — free locked */
  lockedHeadline: 'Stop re-sending screenshots that fall apart in the GC thread',
  lockedBody:
    'Free shows the shape of risk. Estimator unlocks the Receipt habit; Pro opens the bid desk; IC ships the counsel ZIP for one capital site. Climb one step at a time.',

  /** Checkout / post-pay */
  deliveryHint:
    'After Stripe payment, run a site lookup with this email — then download the IC Diligence Bundle ZIP from results (memo + boardroom PDF + DOCX + Excel).',
  successBody:
    'Payment confirmed. Re-run your site lookup with this same email and choose Generate IC Report — then download the Diligence Bundle ZIP (decision memo + boardroom PDF + counsel DOCX + Excel workbook + optional CSVs).',
  confirmPromptIntro: 'Generate IC Diligence Bundle for:',
  confirmPromptBody:
    'OK uses your IC Project purchase for THIS address only (decision memo + boardroom PDF + DOCX + Excel — no new charge for this paid site). A different address needs a new $1,500 purchase. Cancel researches without the paid package. Reg Guard does not store your credit card.',

  /** FAQ */
  faqWhatYouGet:
    'IC Project ($1,500) is a one-time Diligence Bundle ZIP for one site: 1-page decision memo (HOLD/CLEAR stamp), full boardroom PDF, editable counsel DOCX with evidence binder and live hyperlinks, estimator Excel workbook (Fees · Punch · Evidence), standalone evidence index Excel, optional CSV paste exports, and — for large-load sites — AHJ / interconnect / water parallel clocks. Not a quote, sealed bid, interconnection study, geotech report, or AHJ filing.',

  /** Methodology track title */
  methodologyTitle: 'Track B — IC Diligence Bundle ($1,500)',
  methodologyStep2Title: 'Research + counsel ZIP',

  /** Honest boundary */
  notThis:
    'Not a quote, sealed bid, interconnection study, geotech report, Phase I ESA, or AHJ filing. Planning aid — confirm every fee and timeline with the AHJ before bid.',

  /** Orders / nav short */
  ordersHint:
    'IC Project unlocks the Diligence Bundle ZIP from your IC-depth results — memo + boardroom PDF + counsel DOCX + Excel. Re-download parts anytime from My Orders when available.',
  navDescription: 'IC Diligence Bundle — counsel ZIP',
} as const;

export type IcBundleContent = (typeof IC_BUNDLE.contents)[number];
