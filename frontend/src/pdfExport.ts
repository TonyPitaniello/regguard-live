/**
 * Slim analysis payloads for PDF endpoints.
 * Full IC results can be several MB (scout markdown) and fail POST / 413 / timeout.
 */

export function analysisForPdfExport(view: Record<string, unknown>, researchId?: string | null) {
  const punch =
    (view.punch_list as
      | { punch_list?: unknown[]; timeline_summary?: string; estimated_total_cost?: number }
      | undefined) || {};
  const env =
    (view.environmental_screening as { risk_level?: string; findings?: unknown[] } | undefined) ||
    {};
  return {
    research_id: researchId || view.research_id,
    share_url: view.share_url,
    project_info: view.project_info,
    coverage: view.coverage,
    contingency_band: view.contingency_band,
    ahj_card: view.ahj_card,
    fee_card: view.fee_card,
    gotcha_watchlist: view.gotcha_watchlist,
    inspection_sequence_card: view.inspection_sequence_card,
    document_checklist: view.document_checklist,
    local_pack: view.local_pack,
    margin_killers: Array.isArray(view.margin_killers) ? view.margin_killers.slice(0, 12) : [],
    punch_list: {
      punch_list: Array.isArray(punch.punch_list) ? punch.punch_list.slice(0, 40) : [],
      timeline_summary: punch.timeline_summary,
      estimated_total_cost: punch.estimated_total_cost,
    },
    regguard_stamp: view.regguard_stamp,
    stamp_grade: view.stamp_grade,
    stamp_valid_until: view.stamp_valid_until,
    dc_positioning: view.dc_positioning,
    parallel_clocks: view.parallel_clocks,
    environmental_screening: {
      risk_level: env.risk_level,
      findings: Array.isArray(env.findings) ? env.findings.slice(0, 8) : [],
    },
    honesty: view.honesty,
    preview: view.preview,
    research_depth: view.research_depth,
    depth_tier: view.depth_tier,
    depth_badge: view.depth_badge,
    summary: view.summary,
    paid_local: view.paid_local,
  };
}

export function apiErrorDetail(data: unknown, fallback: string): string {
  if (!data || typeof data !== 'object') return fallback;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    return (
      detail
        .map((d) => (typeof d === 'string' ? d : (d as { msg?: string })?.msg || ''))
        .filter(Boolean)
        .join('; ') || fallback
    );
  }
  return fallback;
}

function siteLineFromView(view: Record<string, unknown> | null | undefined): string {
  const pi = (view?.project_info as Record<string, unknown> | undefined) || {};
  const street = String(pi.address || '').trim();
  const city = String(pi.city || '').trim();
  const state = String(pi.state || '').trim();
  const zip = String(pi.zip || pi.zip_code || '').trim();
  const place = [city, state].filter(Boolean).join(', ');
  const withZip = zip ? `${place} ${zip}`.trim() : place;
  if (street && withZip && !street.toLowerCase().includes(withZip.toLowerCase())) {
    return `${street}, ${withZip}`;
  }
  return street || withZip || 'PROJECT SITE';
}

/** ADDRESS — DOC TYPE in ALL CAPS (matches backend artifact_naming). */
export function artifactDisplayTitle(
  view: Record<string, unknown> | null | undefined,
  docKind: string
): string {
  const site = siteLineFromView(view).replace(/\s+/g, ' ').toUpperCase();
  const kind = String(docKind || 'DOCUMENT')
    .replace(/\s+/g, ' ')
    .toUpperCase();
  return `${site} — ${kind}`;
}

export function artifactDownloadFilename(
  view: Record<string, unknown> | null | undefined,
  docKind: string,
  ext: string
): string {
  const combined = `${siteLineFromView(view)}_${docKind}`.toUpperCase();
  const slug =
    combined
      .replace(/[^A-Z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 160) || 'REGGUARD_DOCUMENT';
  const e = String(ext || 'pdf')
    .replace(/^\./, '')
    .toLowerCase() || 'pdf';
  return `${slug}.${e}`;
}

function filenameFromHeaders(res: Response, fallback: string): string {
  const named = res.headers.get('X-RegGuard-Filename');
  if (named && named.trim()) return named.trim();
  const disp = res.headers.get('Content-Disposition') || '';
  const m = /filename="([^"]+)"/i.exec(disp);
  return (m && m[1]) || fallback;
}

export async function postPdfDownload(
  url: string,
  body: Record<string, unknown>,
  filename: string
): Promise<void> {
  await postBinaryDownload(url, body, filename, ['application/pdf']);
}

/** Shared binary download for PDF / DOCX with clear API error surfacing. */
export async function postBinaryDownload(
  url: string,
  body: Record<string, unknown>,
  filename: string,
  acceptTypes: string[]
): Promise<void> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 90000);
  let res: Response;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'omit',
      signal: controller.signal,
      body: JSON.stringify(body),
    });
  } catch (err) {
    if (err && typeof err === 'object' && (err as { name?: string }).name === 'AbortError') {
      throw new Error('Download timed out — try again or refresh.');
    }
    throw new Error('Could not reach the download service. Check the connection and try again.');
  } finally {
    window.clearTimeout(timer);
  }

  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    if (res.status === 404) {
      throw new Error(
        apiErrorDetail(
          data,
          'Download endpoint not found on the API — deploy the latest backend (Render Manual Deploy), then retry.'
        )
      );
    }
    throw new Error(apiErrorDetail(data, `Download failed (${res.status})`));
  }

  const matched = acceptTypes.some((t) => ctype.includes(t.toLowerCase()));
  if (!matched) {
    const data = await res.json().catch(() => ({}));
    const rawUrl = String((data as { download_url?: string }).download_url || '');
    if (!rawUrl) {
      throw new Error(
        apiErrorDetail(
          data,
          `Server returned ${ctype || 'unknown type'} instead of the file. Try again.`
        )
      );
    }
    const fileRes = await fetch(rawUrl, { credentials: 'omit' });
    if (!fileRes.ok) throw new Error(`File download failed (${fileRes.status})`);
    await saveBlob(await fileRes.blob(), filenameFromHeaders(fileRes, filename));
    return;
  }
  await saveBlob(await res.blob(), filenameFromHeaders(res, filename));
}

import { downloadOnlyBlob } from './openAndDownload';

/** Save to disk — caller is already in a results/viewer Forward·Download context. */
async function saveBlob(blob: Blob, filename: string): Promise<void> {
  await downloadOnlyBlob(blob, filename);
}
