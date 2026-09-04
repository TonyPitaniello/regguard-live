/**
 * Twilio A2P resubmit field values — copy into Console.
 * Keep in sync with /a2p-evidence, /sms-opt-in, Privacy, Terms.
 */

export const A2P_WEBSITE = 'https://app.regguardagent.com/';
export const A2P_PRIVACY = 'https://app.regguardagent.com/privacy';
export const A2P_TERMS = 'https://app.regguardagent.com/terms';
export const A2P_SMS_OPT_IN = 'https://app.regguardagent.com/sms-opt-in';
export const A2P_EVIDENCE = 'https://app.regguardagent.com/a2p-evidence';

export const A2P_CAMPAIGN_DESCRIPTION =
  'Optional transactional SMS from RegGuard / Pitaniello Perkins LLC: Bid Risk Receipt links, diligence summaries, order/PDF notices, and ZIP-watch alerts. Users can run lookups and get email results without ever opting into SMS. Not marketing.';

export const A2P_MESSAGE_FLOW = `SMS is OPTIONAL and is NEVER required to sign up or use RegGuard.

PROOF — email-only signup / free lookup (no phone, no SMS checkbox): https://app.regguardagent.com/signup-without-sms and the live home form at https://app.regguardagent.com/ (email only). Paid signup at /signup is email + password + company only.

Optional SMS is a SEPARATE step after Results:
(1) User finishes a lookup without SMS.
(2) On Results they may open Text results OR skip it and use Email me / the web report.
(3) If they want texts, they enter a mobile number, check a SEPARATE unchecked-by-default SMS consent checkbox, and tap Text me. Leaving the box unchecked does not block the service.
(4) Same optional UI: https://app.regguardagent.com/sms-opt-in · full packet: https://app.regguardagent.com/a2p-evidence

Opted-in users get transactional SMS from RegGuard / Pitaniello Perkins LLC (receipts, order/PDF notices, ZIP-watch if enabled). Message frequency varies. Message and data rates may apply. STOP / HELP. We do not share mobile numbers or messaging consent for marketing.

Privacy: https://app.regguardagent.com/privacy
Terms: https://app.regguardagent.com/terms`;

export const A2P_SAMPLE_1 =
  'RegGuard: Your Bid Risk Receipt for Midlothian, TX 76065 is ready. Open: https://app.regguardagent.com/r/example Reply STOP to cancel, HELP for help.';

export const A2P_SAMPLE_2 =
  'RegGuard: Local diligence changed for ZIP 75074. Re-run for a fresh stamp: https://app.regguardagent.com/jobs Msg & data rates may apply. Reply STOP to cancel.';
