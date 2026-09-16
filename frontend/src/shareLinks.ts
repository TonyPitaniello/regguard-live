/** Append ?ref= + campaign UTMs to a Bid Risk Receipt URL. */

export const SHARE_UTM = {
  utm_source: 'receipt',
  utm_medium: 'share',
  utm_campaign: 'bid_risk_receipt',
} as const;

export function storedReferralCode(): string {
  try {
    return (
      sessionStorage.getItem('referralCode') ||
      localStorage.getItem('referralCode') ||
      sessionStorage.getItem('affiliateCode') ||
      ''
    )
      .trim()
      .toLowerCase();
  } catch {
    return '';
  }
}

export function rememberReferralCode(code: string) {
  const c = (code || '').trim().toLowerCase();
  if (!c) return;
  try {
    sessionStorage.setItem('referralCode', c);
    localStorage.setItem('referralCode', c);
    sessionStorage.setItem('affiliateCode', c);
  } catch {
    /* ignore */
  }
}

export function withShareParams(
  url: string,
  ref?: string | null,
  extra?: Record<string, string>
): string {
  const raw = (url || '').trim();
  if (!raw) return '';
  try {
    const u = new URL(raw, 'https://app.regguardagent.com');
    const code = (ref || storedReferralCode() || '').trim().toLowerCase();
    if (code) u.searchParams.set('ref', code);
    Object.entries(SHARE_UTM).forEach(([k, v]) => {
      if (!u.searchParams.get(k)) u.searchParams.set(k, v);
    });
    if (extra) {
      Object.entries(extra).forEach(([k, v]) => {
        if (v) u.searchParams.set(k, v);
      });
    }
    return u.toString();
  } catch {
    return raw;
  }
}
