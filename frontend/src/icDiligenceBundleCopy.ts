/**
 * Canonical marketing copy for the $1,500 IC Diligence Bundle.
 * Import from here so Pricing / Checkout / Results / Methodology stay consistent.
 */

export const IC_BUNDLE = {
  productName: 'IC Diligence Bundle',
  tierName: 'IC Project Report',
  priceLabel: '$1,500',
  billing: 'one-time per site',
  segment: 'IC · Owner’s Rep · Sponsor · Lender',

  /** Short badge / nav / price strip */
  badge: 'Counsel-ready ZIP for one site',

  /** Hero / card one-liner */
  oneLiner:
    'The diligence package counsel and lenders actually open: a 1-page HOLD/CLEAR stamp, an editable Word brief with live source links and numbered exhibits, fee/punch CSV your estimator can paste, and a parallel-clocks track for AHJ vs interconnect vs water.',

  /** Slightly shorter for dense cards */
  cardDescription:
    'Counsel-ready ZIP for one site — decision memo, editable DOCX with evidence binder, fee/punch CSV, evidence index, and data-center parallel clocks. Not a quote, sealed bid, interconnection study, geotech report, or AHJ filing.',

  /** Emotional draw — why buy */
  whyBuy:
    'Stop forwarding screenshots that counsel rejects. Walk into the LOI / IC call with a citeable package: what to HOLD or CLEAR, why contingency exists, which exhibit backs each claim, and which clocks can slip independently.',

  /** Who it’s for */
  forWhom:
    'Built for independent consultants, owner’s reps, and permitting strategists screening commercial–industrial and data-center-adjacent sites — especially Dallas · Plano · Fort Worth · Austin.',

  /** ZIP contents — benefit-led */
  contents: [
    {
      file: '01 · Decision memo PDF',
      label: '1-page HOLD / CLEAR stamp',
      detail:
        'Bid Risk Receipt: contingency band, top 3 drivers, Source or Unverified — the artifact you forward in one tap.',
    },
    {
      file: '02 · Counsel DOCX',
      label: 'Editable Word for redlines',
      detail:
        'Boardroom brief with live hyperlinks, evidence binder (EX-001…), and claim map counsel can mark up.',
    },
    {
      file: '03 · Fee / punch CSV',
      label: 'Estimator-ready schedule',
      detail:
        'Trade · owner · due window · exhibit_id · source_url — paste into your model or share with the GC.',
    },
    {
      file: '04 · Evidence index CSV',
      label: 'Numbered exhibit map',
      detail:
        'Every cited claim → exhibit ID → source URL. No orphan screenshots.',
    },
    {
      file: 'Inside the DOCX',
      label: 'DC parallel clocks',
      detail:
        'AHJ permits · utility interconnect · water / NPDES as independent tracks — so schedule risk isn’t collapsed into one fake date.',
    },
  ] as const,

  /** Bullet list for pricing / checkout feature arrays */
  featureBullets: [
    'ZIP download: decision memo + counsel DOCX + fee/punch CSV + evidence index',
    '1-page HOLD/CLEAR decision memo (Bid Risk Receipt) — forwardable stamp',
    'Editable counsel DOCX with live source hyperlinks + evidence binder (EX-00N)',
    'Fee / punch CSV: trade · owner · due window · exhibit_id · source_url',
    'Evidence index — every claim mapped to a numbered exhibit',
    'Data-center parallel clocks: AHJ · interconnect · water/NPDES',
    'Strongest citeable coverage today: Dallas / Plano / Austin TX',
  ] as const,

  /** Annual upsell */
  annualDescription:
    'Regenerate the same IC Diligence Bundle ZIP for additional sites after your first IC Project.',
  annualFeatures: [
    'Regenerate ZIP bundles for new site addresses',
    'Same decision memo + counsel DOCX + CSV + evidence package',
    'Strongest citeable coverage: Dallas / Plano / Austin TX',
    'Email support via support@regguardagent.com',
  ] as const,

  /** CTAs */
  ctaBuy: 'Get IC Diligence Bundle — $1,500',
  ctaOrder: 'Order IC Diligence Bundle',
  ctaDownload: 'Download IC Diligence Bundle (ZIP)',
  ctaUnlock: 'Unlock IC Diligence Bundle',
  ctaGenerate: 'Generate IC Diligence Bundle for this site',

  /** Results — paid ready */
  readyHeadline: 'Your IC Diligence Bundle is ready',
  readyBody:
    'Primary $1,500 deliverable: one ZIP with the decision memo, counsel DOCX (evidence binder + hyperlinks), fee/punch CSV, and evidence index. The PDF stamp is for forwarding; the DOCX + CSVs are what counsel and estimators work in.',

  /** Results — owns IC but wrong depth */
  generateHeadline: 'IC access on file — generate the Diligence Bundle for this site',
  generateBody:
    'This run is still free / Pro depth. Re-run with Generate IC Report to unlock the counsel ZIP: memo + DOCX + CSV + evidence binder.',

  /** Results — Pro upsell */
  upsellHeadline: 'Need counsel-ready deliverables for this site?',
  upsellBody:
    'Contractor Pro is for weekly bid habit. IC Project ($1,500) unlocks the Diligence Bundle ZIP — decision memo, editable DOCX with exhibits, fee/punch CSV, and parallel clocks — for this address.',

  /** Results — free locked */
  lockedHeadline: 'IC Diligence Bundle locked',
  lockedBody:
    'Free preview shows the Bid Risk Receipt structure. Partner / Pro deepen monthly lookups. Only an IC Project run unlocks the counsel-ready ZIP for this site.',

  /** Checkout / post-pay */
  deliveryHint:
    'After Stripe payment, run a site lookup with this email — then download the IC Diligence Bundle ZIP from results (memo + DOCX + CSVs). Optional longer boardroom PDF is secondary.',
  successBody:
    'Payment confirmed. Re-run your site lookup with this same email and choose Generate IC Report — then download the Diligence Bundle ZIP (decision memo + counsel DOCX + fee/punch CSV + evidence index).',
  confirmPromptIntro: 'Generate IC Diligence Bundle for:',
  confirmPromptBody:
    'OK builds the $1,500 counsel ZIP for this address from your IC purchase (decision memo + DOCX + CSV + evidence — no new charge here). Cancel researches without the paid package. Reg Guard does not store your credit card.',

  /** FAQ */
  faqWhatYouGet:
    'IC Project ($1,500) is a one-time Diligence Bundle ZIP for one site: 1-page decision memo (HOLD/CLEAR stamp), editable counsel DOCX with evidence binder and live hyperlinks, fee/punch CSV (trade · owner · due window · exhibit_id), evidence index, and — for large-load sites — AHJ / interconnect / water parallel clocks. Longer boardroom PDF is optional. Not a quote, sealed bid, interconnection study, geotech report, or AHJ filing.',

  /** Methodology track title */
  methodologyTitle: 'Track B — IC Diligence Bundle ($1,500)',
  methodologyStep2Title: 'Research + counsel ZIP',

  /** Honest boundary */
  notThis:
    'Not a quote, sealed bid, interconnection study, geotech report, Phase I ESA, or AHJ filing. Planning aid — confirm every fee and timeline with the AHJ before bid.',

  /** Orders / nav short */
  ordersHint:
    'IC Project unlocks the Diligence Bundle ZIP from your IC-depth results — memo + counsel DOCX + CSVs. Re-download parts anytime from My Orders when available.',
  navDescription: 'IC Diligence Bundle — counsel ZIP',
} as const;

export type IcBundleContent = (typeof IC_BUNDLE.contents)[number];
