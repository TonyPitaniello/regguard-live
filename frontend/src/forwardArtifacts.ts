/**
 * Forward / text helpers for results artifacts.
 * Web apps cannot attach arbitrary PDFs to SMS reliably — we text a share URL
 * (and optional short memo). Recipients open the link to download PDFs.
 */

export function reportShareUrl(
  analysis: { share_url?: string; research_id?: string } | null | undefined,
  researchId?: string | null
): string {
  const rid = String(analysis?.research_id || researchId || '').trim();
  let share = String(analysis?.share_url || '').trim();
  if (share.includes('/r/') && !share.endsWith('/r/') && !share.endsWith('/r')) {
    return share;
  }
  if (rid && !rid.startsWith('ephemeral-')) {
    return `https://app.regguardagent.com/r/${encodeURIComponent(rid)}`;
  }
  return share || '';
}

export function openNativeSms(phoneDigits: string, body: string): void {
  const digits = phoneDigits.replace(/\D/g, '').slice(-10);
  const encoded = encodeURIComponent(body);
  const href = /iPhone|iPad|iPod/i.test(navigator.userAgent)
    ? digits
      ? `sms:+1${digits}&body=${encoded}`
      : `sms:&body=${encoded}`
    : digits
      ? `sms:+1${digits}?body=${encoded}`
      : `sms:?body=${encoded}`;
  window.location.href = href;
}

/** Open Messages with a prefilled body (recipient optional — user picks contact). */
export function textResultsToOthers(body: string): void {
  openNativeSms('', body);
}

export function buildArtifactTextMessage(opts: {
  artifactName: string;
  site?: string;
  shareUrl: string;
  extraLines?: string[];
}): string {
  const lines = [
    `Reg Guard — ${opts.artifactName}`,
    opts.site ? `Site: ${opts.site}` : '',
    ...(opts.extraLines || []),
    '',
    opts.shareUrl
      ? `Open / download: ${opts.shareUrl}`
      : 'Open Reg Guard results to download this file.',
    '',
    'Planning aid only — confirm with AHJ before bid.',
  ].filter(Boolean);
  return lines.join('\n');
}

export function downloadTextFile(filename: string, contents: string): void {
  const blob = new Blob([contents], { type: 'text/plain;charset=utf-8' });
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      ta.remove();
      return ok;
    } catch {
      return false;
    }
  }
}
