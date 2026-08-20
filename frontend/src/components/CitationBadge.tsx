/**
 * CitationBadge — every claim shows SOURCE, LINK (portal), or Unverified.
 * Reverse-benchmark: citeability is the product, not optional chrome.
 */

function isHttpUrl(value?: string | null): value is string {
  if (!value) return false;
  const v = value.trim().toLowerCase();
  return v.startsWith('http://') || v.startsWith('https://');
}

export type CitationFields = {
  source_url?: string | null;
  source_label?: string | null;
  verified?: boolean | null;
  citation_tier?: string | null;
  data_sources?: string[] | null;
  cost_verified?: boolean | null;
  estimated_cost?: number | null;
};

export type CitationKind = 'source' | 'link' | 'unverified';

export function citationStatus(fields: CitationFields): {
  kind: CitationKind;
  url: string | null;
  label: string | null;
} {
  const fromListHttp = (fields.data_sources || []).map((s) => s.trim()).find((s) => isHttpUrl(s));
  const url = (isHttpUrl(fields.source_url) && fields.source_url!.trim()) || fromListHttp || null;
  const label =
    (fields.source_label || '').trim() ||
    (fields.data_sources || []).find((s) => s && !isHttpUrl(s)) ||
    null;

  const tier = String(fields.citation_tier || '').toLowerCase();
  if (tier === 'verified' || tier === 'source') {
    return { kind: url ? 'source' : 'unverified', url, label: label || 'Source' };
  }
  if (tier === 'link') {
    return { kind: url ? 'link' : 'unverified', url, label: label || 'Portal link' };
  }
  if (tier === 'unverified') {
    return { kind: 'unverified', url, label };
  }

  // Strict: SOURCE only when verified === true (portal URLs alone are LINK)
  if (url && fields.verified === true) {
    return { kind: 'source', url, label: label || 'Source' };
  }
  if (url) {
    return { kind: 'link', url, label: label || 'Portal link' };
  }
  return { kind: 'unverified', url: null, label };
}

export default function CitationBadge({
  source_url,
  source_label,
  verified,
  citation_tier,
  data_sources,
  cost_verified,
  estimated_cost,
}: CitationFields) {
  const status = citationStatus({
    source_url,
    source_label,
    verified,
    citation_tier,
    data_sources,
  });
  const showCostUnverified =
    estimated_cost != null && estimated_cost > 0 && cost_verified !== true;

  return (
    <div className="flex flex-wrap items-center gap-2 mt-2">
      {status.kind === 'source' && status.url ? (
        <a
          href={status.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wide bg-emerald-500/15 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/25 transition"
        >
          <span aria-hidden>↗</span>
          {status.label || 'Source'}
        </a>
      ) : status.kind === 'link' && status.url ? (
        <a
          href={status.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wide bg-sky-500/15 text-sky-200 border border-sky-500/40 hover:bg-sky-500/25 transition"
        >
          <span aria-hidden>↗</span>
          {status.label || 'Portal link'}
        </a>
      ) : (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wide bg-amber-500/15 text-amber-200 border border-amber-500/40">
          Unverified
        </span>
      )}
      {showCostUnverified && (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wide bg-slate-700/80 text-gray-300 border border-slate-500/50">
          $ estimate unverified
        </span>
      )}
      {status.kind === 'unverified' && status.label && (
        <span className="text-[11px] text-gray-500 truncate max-w-[220px]" title={status.label}>
          {status.label}
        </span>
      )}
    </div>
  );
}
