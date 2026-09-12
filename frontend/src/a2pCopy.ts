/**
 * Twilio A2P resubmit field values — copy into Console.
 * Keep in sync with /a2p-evidence, /sms-opt-in, Privacy, Terms.
 *
 * Opt-in method: WEBSITE ONLY (no keyword, verbal, paper, or QR).
 */

export const A2P_WEBSITE = 'https://app.regguardagent.com/';
export const A2P_PRIVACY = 'https://app.regguardagent.com/privacy';
export const A2P_TERMS = 'https://app.regguardagent.com/terms';
export const A2P_SMS_OPT_IN = 'https://app.regguardagent.com/sms-opt-in';
export const A2P_EVIDENCE = 'https://app.regguardagent.com/a2p-evidence';

export const A2P_CAMPAIGN_DESCRIPTION =
  'Optional transactional SMS from RegGuard / Pitaniello Perkins LLC: Bid Risk Receipt links, diligence summaries, order/PDF notices, and ZIP-watch alerts. Users can run lookups and get email results without ever opting into SMS. Website opt-in only. Not marketing.';

/** Paste into Twilio Campaign → message_flow (website opt-in only). */
export const A2P_MESSAGE_FLOW = `Opt-in method: WEBSITE ONLY. RegGuard does not use keyword text-in, verbal, paper, QR, or shared/third-party consent.

Who opts in: US contractors / users of RegGuard (Pitaniello Perkins LLC) who choose optional SMS after a site lookup.

Where opt-in happens (phone number + SMS consent checkbox are on the SAME form):
(1) User visits https://app.regguardagent.com/ and completes a free site lookup with EMAIL ONLY (phone is not collected on the home form). Email-only proof: https://app.regguardagent.com/signup-without-sms
(2) After Results load, the user may open “Text results (SMS)” OR skip SMS and use Email me / the web report.
(3) To opt in they enter a US mobile number and check a SEPARATE unchecked-by-default consent checkbox on that SAME form naming RegGuard / Pitaniello Perkins LLC (consent text says texts go to the mobile number entered above), then tap Text me. Leaving the box unchecked does not block the service.
(4) Public screenshotable SMS opt-in form (phone field + consent checkbox together): https://app.regguardagent.com/sms-opt-in
(5) Full evidence packet: https://app.regguardagent.com/a2p-evidence

Consent disclosures shown before Text me: transactional SMS about this research request, Bid Risk Receipt / share links, order or PDF-ready notices, and ZIP-watch alerts if enabled; message frequency varies; message and data rates may apply; Reply STOP to opt out; HELP for help; consent is not a condition of purchase; mobile numbers and messaging consent are not shared with third parties or affiliates for marketing. Links: Privacy https://app.regguardagent.com/privacy · Terms https://app.regguardagent.com/terms

Privacy Policy states mobile numbers are not shared with third parties/affiliates for marketing, message frequency varies, and message and data rates may apply.`;

export const A2P_SAMPLE_1 =
  'RegGuard: Your Bid Risk Receipt for Midlothian, TX 76065 is ready. Open: https://app.regguardagent.com/r/example Msg & data rates may apply. Reply STOP to cancel, HELP for help.';

export const A2P_SAMPLE_2 =
  'RegGuard: Local diligence changed for ZIP 75074. Re-run for a fresh stamp: https://app.regguardagent.com/jobs Msg & data rates may apply. Reply STOP to cancel, HELP for help.';
