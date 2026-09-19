/**
 * Slim analysis payloads for PDF endpoints.
 * Full IC results can be several MB (scout markdown) and fail POST / 413 / timeout.
 */

export function analysisForPdfExport(view: Record<string, unknown>, researchId?: string | null) {
  const punch = (view.punch_list as { punch_list?: unknown[]; timeline_summary?: string; estimated_total_cost?: number } | undefined) || {};
  const env = (view.environmental_screening as { risk_level?: string; findings?: unknown[] } | undefined) || {};
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
    return detail
      .map((d) => (typeof d === 'string' ? d : (d as { msg?: string })?.msg || ''))
      .filter(Boolean)
      .join('; ') || fallback;
  }
  return fallback;
}

export async function postPdfDownload(
  url: string,
  body: Record<string, unknown>,
  filename: string
): Promise<void> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 60000);
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
      throw new Error('PDF timed out — try again with a smaller run or refresh.');
    }
    throw new Error('Could not reach the PDF service. Check the connection and try again.');
  } finally {
    window.clearTimeout(timer);
  }

  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(apiErrorDetail(data, `PDF failed (${res.status})`));
  }
  if (!ctype.includes('application/pdf')) {
    const data = await res.json().catch(() => ({}));
    const rawUrl = String((data as { download_url?: string }).download_url || '');
    if (!rawUrl) throw new Error('Server did not return a PDF. Try again.');
    const fileRes = await fetch(rawUrl, { credentials: 'omit' });
    if (!fileRes.ok) throw new Error(`PDF download failed (${fileRes.status})`);
    await saveBlob(await fileRes.blob(), filename);
    return;
  }
  await saveBlob(await res.blob(), filename);
}

async function saveBlob(blob: Blob, filename: string): Promise<void> {
  if (!blob || blob.size < 80) throw new Error('PDF was empty — try again.');
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
