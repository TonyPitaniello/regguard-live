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

  /**
   * Said wherever the City Pack and the ZIP both appear.
   * The pack keeps the estimate. The ZIP is the letter-of-intent packet.
   */
  deskAndZip:
    'The $149 City Pack is the fee sheet for the estimate, and the ZIP is what the lawyer marks up the day before the letter of intent, so someone pricing a bid still needs the pack and someone walking into that meeting needs the ZIP.',

  /**
   * $15,000 stays. Ten sites tie. The 11th is the first one the year saves.
   * Count addresses not yet paid for. This is not the $149 lookup plan.
   */
  annualMath:
    'Ten checkouts at $1,500 equal the $15,000 year. The next address is where the year costs less. Buy the year when you can see about ten capital addresses you have not paid for yet. Daily lookups stay on Contractor Pro at $149 a month.',

  /** Hero / card one-liner — keep in lockstep with Pricing pitch */
  oneLiner:
    'Counsel-ready ZIP for one capital site. The $149 City Pack is the fee sheet for the estimate, and the ZIP is what the lawyer marks up the day before the letter of intent, so someone pricing a bid still needs the pack and someone walking into that meeting needs the ZIP.',

  /** Slightly shorter for dense cards / IC Project tier card */
  cardDescription:
    'Counsel-ready ZIP for one site — decision memo, boardroom PDF, editable Word, and Excel. The $149 City Pack is the fee sheet for the estimate, and the ZIP is what the lawyer marks up the day before the letter of intent, so someone pricing a bid still needs the pack and someone walking into that meeting needs the ZIP.',

  /** Emotional draw — why buy */
  whyBuy:
    'Page one names the fee line or the inspection sequence and attaches the page. Where the schedule states no dollar, the line says confirm-on-schedule and prints no number. The Word file is the one counsel marks up. The three desks are the city intake, the utility that serves this address, and the water or drainage reviewer. You still place the calls.',

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
      label: '1-page memo you forward as it comes out',
      detail:
        'The fee line or inspection sequence, the page that states it, and confirm-on-schedule with no number where the schedule is silent. Plus the three desks for this address.',
    },
    {
      file: '02 · Boardroom PDF',
      label: 'Full boardroom brief',
      detail:
        'The memo again, then the fee rows, the punch, the exhibits, and the three clocks. Every source line is the full https URL.',
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
    '1-page decision memo you forward as generated — fee line or sequence, with the page attached',
    'Full boardroom PDF — punch list, exhibits, parallel clocks',
    'Editable counsel DOCX with live source hyperlinks + evidence binder (EX-00N)',
    'Estimator Excel: Fees · Punch · Evidence sheets (trade · owner · due window · exhibit_id)',
    'Evidence index Excel: Exhibits · Claims · Index — every claim mapped to a numbered exhibit',
    'Optional CSV paste exports of the same schedule + evidence index',
    'Data-center parallel clocks: AHJ · interconnect · water/NPDES',
    'Strongest citeable coverage today: Dallas / Plano / Austin / Fort Worth',
  ] as const,

  /**
   * Annual — sell firm volume on capital sites; soft-gate overuse without jargon.
   * Premortem-hardened:
   *   - No “Pro spray” / “shop rate” / “outside-seat” jargon
   *   - Ten sites tie at $15,000. The 11th is where the year costs less. Not a purchase minimum.
   *   - Speak to IC / owner’s rep / lender who *are* the diligence seat — not only “brief counsel”
   */
  annualDescription:
    'Ten checkouts at $1,500 equal the $15,000 year. The next address is where the year costs less. Buy the year when you can see about ten capital addresses you have not paid for yet. Daily lookups stay on Contractor Pro at $149 a month.',
  annualFeatures: [
    'Same Diligence Bundle ZIP for each new bound capital site on this purchase email',
    'Memo · boardroom PDF · counsel Word · Excel exhibits — every address',
    'Ten sites at $1,500 equal $15,000. The 11th address is where the year costs less',
    'Count capital addresses you have not paid for yet. Earlier checkouts are not refunded',
    'Each site still needs its own three calls. This does not include Contractor Pro lookups',
    'Strongest citeable coverage: Dallas / Plano / Austin / Fort Worth',
    'Email support via support@regguardagent.com',
  ] as const,
  /** Results / capped-scrape — quality pace; no scrape counter, no firehose invite */
  annualFairUseNote:
    'Annual covers the counsel ZIP for capital sites on this purchase email. Daily lookups stay on Contractor Pro at $149 a month. Generate IC when this address needs the ZIP.',
  /** Wrong-depth body when buyer already has Annual */
  generateBodyAnnual:
    'This run is still free / Pro depth. Re-run with Generate IC to unlock the counsel ZIP for this address under your Annual. Same Diligence Bundle — memo · boardroom · Word · Excel.',

  /** CTAs */
  ctaBuy: 'Get IC Diligence Bundle — $1,500',
  ctaOrder: 'Order IC Diligence Bundle',
  ctaDownload: 'Download IC Diligence Bundle (ZIP)',
  ctaUnlock: 'Unlock IC Diligence Bundle',
  ctaGenerate: 'Generate IC Diligence Bundle for this site',

  /** Results screen, beside the ZIP. Not a file inside the ZIP. */
  forwardLine:
    'Counsel — ZIP for this address before the letter of intent. Page one is the HOLD and the three desks. The Word file is the one to mark up. The calls are still ours.',

  /** Said to a partner counting unpaid capital sites. N is that count. */
  partnerLine:
    'We have N sites left. Ten is a tie. The next one is the expensive way.',

  /** Results — paid ready */
  readyHeadline: 'Your IC Diligence Bundle is ready',
  readyBody:
    'Primary $1,500 deliverable: one ZIP with the decision memo, full boardroom PDF, counsel DOCX (evidence binder + hyperlinks), estimator Excel (Fees · Punch · Evidence), evidence index Excel, and optional CSV paste exports. Parallel clocks are in the boardroom PDF and DOCX. Download individual parts below if you only need one file.',

  /** Results — owns IC but wrong depth */
  generateHeadline: 'Generate the Diligence Bundle for this paid site',
  generateBody:
    'This run is still free / Pro depth. Re-run with Generate IC Report to unlock the counsel ZIP for this address: memo + boardroom PDF + DOCX + Excel. A different address needs a new $1,500 Diligence Bundle. Screening only — not an interconnection study.',

  /** Results — Pro upsell */
  upsellHeadline: 'Counsel won’t mark up a City Pack PDF',
  upsellBody:
    'The $149 City Pack is the fee sheet for the estimate, and the ZIP is what the lawyer marks up the day before the letter of intent, so someone pricing a bid still needs the pack and someone walking into that meeting needs the ZIP.',

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
    'OK uses your IC Diligence Bundle for THIS address only (decision memo + boardroom PDF + DOCX + Excel — no new charge for this paid site). A different address needs a new $1,500 purchase. Cancel researches without the paid package. Reg Guard does not store your credit card.',

  /** FAQ */
  faqWhatYouGet:
    'The IC Diligence Bundle ($1,500) is one ZIP for one site: 1-page decision memo (HOLD/CLEAR stamp), full boardroom PDF, editable counsel DOCX with evidence binder and live hyperlinks, estimator Excel workbook (Fees · Punch · Evidence), standalone evidence index Excel, optional CSV paste exports, and — for large-load sites — AHJ / interconnect / water parallel clocks. Not a quote, sealed bid, interconnection study, geotech report, or AHJ filing.',

  /** Methodology track title */
  methodologyTitle: 'Track B — IC Diligence Bundle ($1,500)',
  methodologyStep2Title: 'Research + counsel ZIP',

  /** Honest boundary */
  notThis:
    'Not a quote, sealed bid, interconnection study, geotech report, Phase I ESA, or AHJ filing. A dollar is printed only when the schedule states it. Where it does not, the cell says confirm-on-schedule.',

  /** Orders / nav short */
  ordersHint:
    'A completed Diligence Bundle unlocks the ZIP from your results — memo, boardroom PDF, counsel Word, and Excel. Re-download parts anytime from My Orders when available.',
  navDescription: 'IC Diligence Bundle — counsel ZIP',
} as const;

export type IcBundleContent = (typeof IC_BUNDLE.contents)[number];
