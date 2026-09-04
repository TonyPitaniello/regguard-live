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

export const A2P_MESSAGE_FLOW = `SMS is OPTIONAL. End users can sign up, run a free or paid site lookup, and receive results by email without providing a mobile number or agreeing to SMS. Consent to SMS is never a condition of creating an account or using RegGuard.

Optional SMS opt-in happens only after a lookup, on a separate Text results panel (not on the signup form):

(1) User visits https://app.regguardagent.com/ and completes a site lookup (email-only is fine; phone on the home form is labeled optional and does not enroll them in SMS).
(2) On Results they may optionally open Text results (SMS). They enter a US mobile number, check a separate unchecked-by-default consent box, and tap Text me. Leaving that box unchecked or skipping Text me still lets them use email delivery and the full web report.
(3) The same optional consent UI is public with no login at https://app.regguardagent.com/sms-opt-in and https://app.regguardagent.com/a2p-evidence.

If they opt in, they receive transactional SMS from RegGuard / Pitaniello Perkins LLC (research results, Bid Risk Receipt / share links, order/PDF notices, and ZIP-watch alerts only if enabled). Message frequency varies. Message and data rates may apply. Reply STOP to cancel; HELP for help. We do not share, sell, or provide mobile numbers or messaging consent to third parties or affiliates for marketing.

Privacy Policy: https://app.regguardagent.com/privacy
Terms of Service: https://app.regguardagent.com/terms`;

export const A2P_SAMPLE_1 =
  'RegGuard: Your Bid Risk Receipt for Midlothian, TX 76065 is ready. Open: https://app.regguardagent.com/r/example Reply STOP to cancel, HELP for help.';

export const A2P_SAMPLE_2 =
  'RegGuard: Local diligence changed for ZIP 75074. Re-run for a fresh stamp: https://app.regguardagent.com/jobs Msg & data rates may apply. Reply STOP to cancel.';
