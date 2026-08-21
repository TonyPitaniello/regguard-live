/**
 * Public shareable report at /r/:id — forwardable into a GC bid file.
 * Mirrors the in-app Bid Risk Receipt essentials (not a thin punch dump).
 */

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AlertCircle, Copy, Check, ExternalLink, Loader2 } from 'lucide-react';
import { backendUrl } from '../env';
import { areEstimatesUnverified, isRiskScoreHidden } from '../components/honesty';
import CitationBadge from '../components/CitationBadge';
import type { AnalysisData } from '../components/ResultsViewerModal';

type ReportPayload = {
  research_id: string;
  share_url: string;
  created_at?: string;
  expires_at?: string;
  preview?: boolean;
  analysis: AnalysisData;
  sources?: Array<{ label: string; url: string }>;
};

function siteLines(analysis: AnalysisData): { street: string; place: string } {
  const street = (analysis.project_info?.address || '').trim();
  const place = [analysis.project_info?.city, analysis.project_info?.state, analysis.project_info?.zip]
    .filter(Boolean)
    .join(', ')
    .replace(/, ([A-Z]{2}), /, ', $1 ');
  const sn = street.toLowerCase().replace(/[^a-z0-9]/g, '');
  const cn = (analysis.project_info?.city || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  if (cn && sn.includes(cn)) {
    return { street, place: '' };
  }
  return { street, place };
}

export default function SharedReportPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!id) {
      setError('Missing report id');
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(backendUrl(`/research/${encodeURIComponent(id)}/report`));
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail.detail || `Report not found (${res.status})`);
        }
        const data = (await res.json()) as ReportPayload;
        if (!cancelled) setReport(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load report');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const copyLink = async () => {
    const url = report?.share_url || window.location.href;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center text-gray-300 gap-3">
        <Loader2 className="w-5 h-5 animate-spin" />
        Loading shareable report…
      </div>
    );
  }

  if (error || !report?.analysis) {
    return (
      <div className="max-w-lg mx-auto my-16 px-4 text-center space-y-4">
        <AlertCircle className="w-8 h-8 text-amber-400 mx-auto" />
        <h1 className="text-2xl font-black text-white">Report unavailable</h1>
        <p className="text-gray-300 text-sm">{error || 'This link may have expired.'}</p>
        <p className="text-gray-400 text-xs">
          This page does not open the address form. If you expected results here, ask the sender to
          re-share from Reg Guard results (the link must look like /r/…uuid…).
        </p>
        <Link to="/jobs" className="inline-flex text-sm font-semibold text-purple-300 hover:text-purple-200">
          Open saved jobs
        </Link>
      </div>
    );
  }

  const analysis = report.analysis;
  const hideRisk = isRiskScoreHidden(analysis);
  const unverified = areEstimatesUnverified(analysis);
  const punch = analysis.punch_list?.punch_list || [];
  const killers = analysis.margin_killers || [];
  const sources = report.sources || [];
  const { street, place } = siteLines(analysis);
  const coverageBadge = analysis.coverage?.badge || analysis.coverage?.badge_short;
  const depthBadge = analysis.depth_badge;
  const band = analysis.contingency_band;
  const localPack = (analysis as { local_pack?: { tier?: string; citeable?: boolean } }).local_pack;
  const localPackLabel = localPack?.tier
    ? localPack.citeable
      ? `Local pack: ${localPack.tier}`
      : `Local pack: ${localPack.tier} (confirm AHJ)`
    : null;

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-3xl mx-auto px-4 py-10 sm:px-6 space-y-8">
        <header className="space-y-3 border-b border-slate-800 pb-6">
          <p className="text-xs font-bold uppercase tracking-wide text-emerald-300">
            RegGuard Bid Risk Receipt
          </p>
          <h1 className="text-3xl font-black">Forwardable site diligence</h1>
          <p className="text-gray-300">
            {street}
            {place ? (
              <>
                <br />
                {place}
              </>
            ) : null}
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {depthBadge && (
              <span className="inline-flex px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide bg-amber-500/15 text-amber-200 border border-amber-500/35">
                {depthBadge}
              </span>
            )}
            {coverageBadge && (
              <span className="inline-flex px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide bg-slate-800 text-gray-200 border border-slate-600">
                {coverageBadge}
              </span>
            )}
            {localPackLabel && (
              <span className="inline-flex px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide bg-indigo-500/15 text-indigo-200 border border-indigo-500/35">
                {localPackLabel}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2 pt-2">
            <button
              type="button"
              onClick={() => void copyLink()}
              className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm font-semibold text-emerald-100 hover:bg-emerald-500/20"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Link copied' : 'Copy share link'}
            </button>
            <a
              href={report.share_url}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-600 px-3 py-2 text-sm text-gray-200"
            >
              <ExternalLink className="w-4 h-4" />
              {report.share_url.replace(/^https?:\/\//, '')}
            </a>
          </div>
        </header>

        {(analysis.preview || hideRisk || unverified) && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            <strong className="text-amber-50">Preview / unverified estimates.</strong> Risk scores are not
            parcel-verified GIS data. Dollar and day figures are not AHJ quotes — confirm before bidding.
          </div>
        )}

        {band?.pct_low != null && band?.pct_high != null && (
          <section className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5">
            <p className="text-xs font-bold uppercase tracking-wide text-emerald-300 mb-1">
              {band.label || 'Suggested bid contingency'}
            </p>
            <p className="text-4xl font-black text-emerald-400 tracking-tight">
              +{band.pct_low}% – +{band.pct_high}%
            </p>
            <p className="text-sm text-gray-300 mt-1">
              mid {band.pct_mid}% · planning aid — not a quote
            </p>
            {band.disclaimer && <p className="text-xs text-gray-500 mt-2">{band.disclaimer}</p>}
          </section>
        )}

        <section className="grid sm:grid-cols-3 gap-3">
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
            <p className="text-xs text-gray-400 mb-1">Risk score</p>
            <p className="text-xl font-black text-amber-200">
              {hideRisk ? 'Unavailable' : analysis.environmental_screening?.risk_level}
            </p>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
            <p className="text-xs text-gray-400 mb-1">Timeline {unverified ? '(unverified)' : ''}</p>
            <p className="text-lg font-bold text-blue-300">{analysis.summary?.estimated_timeline}</p>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
            <p className="text-xs text-gray-400 mb-1">Est. cost {unverified ? '(unverified)' : ''}</p>
            <p className="text-lg font-bold text-emerald-300">
              ${(analysis.summary?.estimated_total_cost || 0).toLocaleString()}
            </p>
          </div>
        </section>

        {killers.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-xl font-bold">Top risk flags</h2>
            <ol className="space-y-3 list-decimal pl-5">
              {killers.slice(0, 3).map((k, i) => (
                <li key={`${k.title}-${i}`} className="text-sm text-gray-200">
                  <span className="text-amber-200 font-semibold text-xs uppercase mr-1">
                    {k.priority || 'NOTE'}
                  </span>
                  <span className="text-white font-medium">{k.title}</span>
                  {k.detail ? <p className="text-gray-400 text-xs mt-0.5">{k.detail}</p> : null}
                  <CitationBadge
                    source_url={k.source_url}
                    source_label={k.source_label}
                    verified={k.verified}
                    citation_tier={k.citation_tier}
                  />
                </li>
              ))}
            </ol>
          </section>
        )}

        <section className="space-y-3">
          <h2 className="text-xl font-bold">Full punch list</h2>
          {punch.length === 0 ? (
            <p className="text-sm text-gray-400">No punch items on this report.</p>
          ) : (
            punch.map((item, idx) => (
              <div key={idx} className="rounded-lg border border-slate-700 bg-slate-900/50 p-4">
                <div className="flex justify-between gap-3">
                  <p className="font-semibold text-white">
                    {idx + 1}. {item.task}
                  </p>
                  <span className="text-xs font-bold text-orange-200 shrink-0">{item.priority}</span>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {item.timeline} · {item.responsible_party}
                  {item.estimated_cost != null
                    ? ` · $${Number(item.estimated_cost).toLocaleString()}${unverified ? ' (unverified)' : ''}`
                    : ''}
                </p>
                {item.notes ? <p className="text-xs text-gray-500 mt-1">{item.notes}</p> : null}
                <CitationBadge
                  source_url={item.source_url}
                  source_label={item.source_label}
                  verified={item.verified}
                  citation_tier={item.citation_tier}
                  cost_verified={item.cost_verified}
                  estimated_cost={item.estimated_cost}
                />
              </div>
            ))
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-bold">Sources</h2>
          <p className="text-xs text-gray-500">
            SOURCE = parcel/scout verified. LINK = official portal URL to confirm yourself. Unverified =
            no defendable URL yet.
          </p>
          {sources.length === 0 ? (
            <p className="text-sm text-gray-400">
              No citeable .gov / Municode URLs in this preview. Full research runs attach sources when
              scout hits exist.
            </p>
          ) : (
            <ul className="space-y-2 text-sm">
              {sources.map((s, i) => (
                <li key={i} className="text-gray-300">
                  {s.url?.startsWith('http') ? (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-300 hover:underline"
                    >
                      {s.label || s.url}
                    </a>
                  ) : (
                    s.label
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        <footer className="border-t border-slate-800 pt-6 text-sm text-gray-400">
          Built for forwarding into a bid file. Confirm every fee and timeline with the AHJ before you
          bid.
          <div className="mt-3">
            <Link to="/jobs" className="text-emerald-300 hover:text-emerald-200 font-semibold">
              Open saved jobs →
            </Link>
          </div>
        </footer>
      </div>
    </div>
  );
}
