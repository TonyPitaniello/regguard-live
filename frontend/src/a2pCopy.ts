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
  'Transactional SMS from RegGuard / Pitaniello Perkins LLC: Bid Risk Receipt links, site diligence summaries, order/PDF-ready notices, and optional ZIP-watch alerts for contractors who opt in on our website. Not marketing.';

export const A2P_MESSAGE_FLOW = `End users opt in on the RegGuard website operated by Pitaniello Perkins LLC at https://app.regguardagent.com/.

How consent is collected: (1) User completes a site lookup, then on Results opens Text results (SMS), enters a US mobile number, checks an unchecked-by-default consent box agreeing to receive transactional SMS from RegGuard / Pitaniello Perkins LLC (research results, Bid Risk Receipt / shareable report links, related order or PDF-ready notices, and Saved Job / ZIP-watch alerts only if the user enables them), then taps Text me. (2) The identical consent UI is publicly viewable with no login at https://app.regguardagent.com/sms-opt-in and summarized for reviewers at https://app.regguardagent.com/a2p-evidence.

Message frequency varies. Message and data rates may apply. Reply STOP to cancel; HELP for help. Consent to SMS is not a condition of purchasing RegGuard services. We do not share, sell, or provide mobile numbers or messaging consent to third parties or affiliates for marketing.

Privacy Policy: https://app.regguardagent.com/privacy
Terms of Service: https://app.regguardagent.com/terms`;

export const A2P_SAMPLE_1 =
  'RegGuard: Your Bid Risk Receipt for Midlothian, TX 76065 is ready. Open: https://app.regguardagent.com/r/example Reply STOP to cancel, HELP for help.';

export const A2P_SAMPLE_2 =
  'RegGuard: Local diligence changed for ZIP 75074. Re-run for a fresh stamp: https://app.regguardagent.com/jobs Msg & data rates may apply. Reply STOP to cancel.';
