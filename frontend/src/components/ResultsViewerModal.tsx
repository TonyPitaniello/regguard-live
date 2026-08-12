/**
 * ResultsViewerModal — large overlay showing free-trial analysis + text/email send.
 * Stays on the current page (homepage / free-trial); does not require /results navigation.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ChevronDown, ChevronUp, Copy, Check, Share2, Sparkles } from 'lucide-react';
import SendResultsForm, { ResultsSummaryPayload } from './SendResultsForm';
import CitationBadge from './CitationBadge';

const APP_URL = 'https://app.regguardagent.com/';

/** Soft-lock: free users see this many punch lines; rest unlock via Pro/IC or share-to-unlock */
const FREE_PUNCH_VISIBLE = 5;
const FREE_FINDINGS_VISIBLE = 3;

export type PunchListItemData = {
  priority: string;
  task: string;
  responsible_party: string;
  timeline: string;
  estimated_cost?: number;
  notes: string;
  source_url?: string | null;
  source_label?: string | null;
  verified?: boolean;
  cost_verified?: boolean;
};

export type CriticalPathItem = string | {
  task: string;
  source_url?: string | null;
  source_label?: string | null;
  verified?: boolean;
  cost_verified?: boolean;
  estimated_cost?: number | null;
};

export interface AnalysisData {
  timestamp: string;
  research_id?: string;
  preview?: boolean;
  research_depth?: string;
  pro_summary_markdown?: string;
  pro_source_urls?: string[];
  project_info: {
    address: string;
    city: string;
    state: string;
    zip: string;
    type: string;
    coordinates?: { latitude: number; longitude: number };
  };
  environmental_screening: {
    risk_level: string;
    findings: Array<{
      category: string;
      risk_level: string;
      description: string;
      action_items: string[];
      data_sources: string[];
      research_cost_usd: number;
    }>;
    total_research_cost: number;
    action_plan: string[];
  };
  punch_list: {
    punch_list: PunchListItemData[];
    timeline_summary: string;
    estimated_total_cost: number;
    critical_path: CriticalPathItem[];
    milestones: Array<{ week: string; milestone: string }>;
    who_to_call: Record<string, string>;
    estimates_verified?: boolean;
  };
  summary: {
    total_environmental_risks: number;
    high_risk_count: number;
    total_punch_list_items: number;
    estimated_timeline: string;
    estimated_total_cost: number;
  };
  next_steps: string[];
}

function criticalPathTask(item: CriticalPathItem): string {
  return typeof item === 'string' ? item : item.task;
}

interface ResultsViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis: AnalysisData;
  researchId?: string | null;
  defaultEmail?: string;
  defaultPhone?: string;
  /** Paid entitlement but current results are still free-depth — offer one-click deepen */
  canUnlockDeeper?: boolean;
  onUnlockDeeper?: () => void;
  unlockLoading?: boolean;
}

function buildShareText(analysis: AnalysisData): string {
  const p = analysis.project_info;
  const risk = analysis.environmental_screening?.risk_level || 'N/A';
  const timeline = analysis.summary?.estimated_timeline || 'TBD';
  const top = (analysis.punch_list?.critical_path || [])
    .slice(0, 3)
    .map((t, i) => `${i + 1}. ${typeof t === 'string' ? t : t.task}`)
    .join('\n');
  return [
    `RegGuard pre-bid punch list (DFW/Austin focus): ${p.address}, ${p.city}, ${p.state} ${p.zip}`,
    `Risk: ${risk} · Timeline: ${timeline}`,
    top ? `Top actions:\n${top}` : '',
    'Every line is citeable or marked Unverified — forward only what you can defend.',
    `Run your site free: ${APP_URL}`,
  ]
    .filter(Boolean)
    .join('\n');
}

function getRiskColor(level: string) {
  switch (level.toUpperCase()) {
    case 'CRITICAL':
      return 'text-red-500 bg-red-50';
    case 'HIGH':
      return 'text-orange-500 bg-orange-50';
    case 'MEDIUM':
      return 'text-yellow-500 bg-yellow-50';
    case 'LOW':
      return 'text-green-500 bg-green-50';
    default:
      return 'text-gray-500 bg-gray-50';
  }
}

function getPriorityBadge(priority: string) {
  switch (priority.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-red-100 text-red-800 border border-red-300';
    case 'HIGH':
      return 'bg-orange-100 text-orange-800 border border-orange-300';
    case 'MEDIUM':
      return 'bg-yellow-100 text-yellow-800 border border-yellow-300';
    case 'LOW':
      return 'bg-blue-100 text-blue-800 border border-blue-300';
    default:
      return 'bg-gray-100 text-gray-800 border border-gray-300';
  }
}

export function buildSummaryFromAnalysis(analysis: AnalysisData): ResultsSummaryPayload {
  return {
    zip: analysis.project_info?.zip,
    city: analysis.project_info?.city,
    state: analysis.project_info?.state,
    address: analysis.project_info?.address,
    risk_level: analysis.environmental_screening?.risk_level,
    timeline: analysis.summary?.estimated_timeline,
    cost: analysis.summary?.estimated_total_cost,
  };
}

export default function ResultsViewerModal({
  isOpen,
  onClose,
  analysis,
  researchId,
  defaultEmail = '',
  defaultPhone = '',
  canUnlockDeeper = false,
  onUnlockDeeper,
  unlockLoading = false,
}: ResultsViewerModalProps) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState({
    environmental: true,
    punchList: true,
    critical: true,
  });
  const [copied, setCopied] = useState<'link' | 'text' | 'facebook' | 'instagram' | null>(null);
  const [toast, setToast] = useState('');
  const [shareUnlocked, setShareUnlocked] = useState(() => {
    if (typeof window === 'undefined') return false;
    return sessionStorage.getItem('shareUnlocked') === '1';
  });

  // Lock body scroll while modal is open so the form/map behind cannot float with page scroll
  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isOpen]);

  if (!isOpen || !analysis) return null;

  const summary = buildSummaryFromAnalysis(analysis);
  const effectiveResearchId = researchId || analysis.research_id || null;
  const shareText = buildShareText(analysis);
  const depth = (analysis.research_depth || '').toLowerCase();
  const isDeep = depth === 'pro' || depth === 'pro_partial';
  const emailForCheckout = (defaultEmail || sessionStorage.getItem('userEmail') || '')
    .trim()
    .toLowerCase();
  // Soft-lock: free sees limited lines unless they shared OR paid deep research
  const softLocked = !isDeep && !shareUnlocked;
  const punchVisible = softLocked ? FREE_PUNCH_VISIBLE : 50;
  const findingsVisible = softLocked ? FREE_FINDINGS_VISIBLE : 12;

  const goCheckout = (tier: 'contractor_pro' | 'ic_project') => {
    // Persist site so return after payment can deepen the same lookup
    try {
      const pi = analysis.project_info;
      sessionStorage.setItem(
        'lastResearchForm',
        JSON.stringify({
          address: pi.address || '',
          city: pi.city || '',
          state: pi.state || '',
          zip: pi.zip || '',
          projectType: pi.type || 'commercial',
          email: emailForCheckout,
        })
      );
      if (emailForCheckout) sessionStorage.setItem('userEmail', emailForCheckout);
      sessionStorage.setItem('pendingDeepUnlock', '1');
    } catch {
      /* ignore */
    }
    const q = emailForCheckout ? `?email=${encodeURIComponent(emailForCheckout)}` : '';
    navigate(`/checkout/${tier}${q}`);
  };

  const grantShareUnlock = () => {
    try {
      sessionStorage.setItem('shareUnlocked', '1');
    } catch {
      /* ignore */
    }
    setShareUnlocked(true);
    setToast('Full free punch list unlocked — forward it to a colleague next.');
    window.setTimeout(() => setToast(''), 4000);
  };

  const toggle = (key: keyof typeof expanded) => {
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(''), 3200);
  };

  const copyShareText = async (kind: 'text' | 'facebook' | 'instagram' = 'text') => {
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(kind);
      window.setTimeout(() => setCopied(null), 2000);
      grantShareUnlock();
      if (kind === 'instagram') {
        showToast('Caption copied — paste in Instagram DM or Story');
      } else if (kind === 'facebook') {
        showToast('Summary copied — paste into your Facebook post');
      }
      return true;
    } catch {
      showToast('Could not copy — select share text manually');
      return false;
    }
  };

  const openWhatsApp = () => {
    window.open(`https://wa.me/?text=${encodeURIComponent(shareText)}`, '_blank', 'noopener,noreferrer');
    grantShareUnlock();
  };

  const openFacebook = async () => {
    await copyShareText('facebook');
    window.open(
      `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(APP_URL)}`,
      '_blank',
      'noopener,noreferrer'
    );
  };

  const openInstagram = async () => {
    await copyShareText('instagram');
    window.open('https://www.instagram.com/', '_blank', 'noopener,noreferrer');
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-2 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="results-modal-title"
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-5xl max-h-[92vh] flex flex-col bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-purple-500/30 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-5 sm:px-8 py-5 border-b border-slate-700/80 bg-slate-900/90 shrink-0 z-10">
          <div>
            <h2 id="results-modal-title" className="text-2xl sm:text-3xl font-black text-white">
              Your Site Diligence Analysis
            </h2>
            <p className="text-gray-400 text-sm mt-1">
              {analysis.project_info.address} • {analysis.project_info.city},{' '}
              {analysis.project_info.state} {analysis.project_info.zip}
            </p>
            {(analysis.research_depth === 'pro' || analysis.research_depth === 'pro_partial') && (
              <p className="mt-2 inline-flex items-center px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                {analysis.research_depth === 'pro'
                  ? 'Contractor Pro — deep research'
                  : 'Contractor Pro — partial deep research'}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-slate-800 transition"
            aria-label="Close results"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Text / Email + social share — always visible without scrolling results */}
        <div className="px-5 sm:px-8 py-4 border-b border-emerald-500/30 bg-slate-950/90 shrink-0 space-y-3">
          <SendResultsForm
            researchId={effectiveResearchId}
            summary={summary}
            defaultEmail={defaultEmail}
            defaultPhone={defaultPhone}
          />

          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-purple-300/90 mb-2 flex items-center gap-2">
              <Share2 className="w-3.5 h-3.5" />
              Share results
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={openWhatsApp}
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg border border-emerald-500/40 bg-emerald-500/10 text-emerald-200 text-sm font-semibold hover:bg-emerald-500/20 transition"
              >
                WhatsApp
              </button>
              <button
                type="button"
                onClick={() => void openFacebook()}
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg border border-blue-500/40 bg-blue-500/10 text-blue-200 text-sm font-semibold hover:bg-blue-500/20 transition"
              >
                Facebook
              </button>
              <button
                type="button"
                onClick={() => void openInstagram()}
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg border border-pink-500/40 bg-pink-500/10 text-pink-200 text-sm font-semibold hover:bg-pink-500/20 transition"
              >
                Instagram
              </button>
              <button
                type="button"
                onClick={() => void copyShareText('text')}
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg border border-purple-500/40 bg-purple-500/10 text-purple-200 text-sm font-semibold hover:bg-purple-500/20 transition"
              >
                {copied === 'text' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                {copied === 'text' ? 'Copied' : 'Copy'}
              </button>
              <button
                type="button"
                onClick={() => void copyShareText('facebook')}
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg border border-slate-600 bg-slate-800/80 text-gray-200 text-sm font-semibold hover:bg-slate-700 transition"
              >
                {copied === 'facebook' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                {copied === 'facebook' ? 'Copied for Facebook' : 'Copy for Facebook'}
              </button>
            </div>
            {toast && (
              <p className="mt-2 text-sm text-emerald-300" role="status">
                {toast}
              </p>
            )}
          </div>
        </div>

        {/* Scrollable body — punch list first (citeable pre-bid artifact) */}
        <div className="flex-1 overflow-y-auto px-5 sm:px-8 py-6 space-y-6">
          <p className="text-xs text-gray-400">
            Every line shows a source link or <span className="text-amber-300 font-semibold">Unverified</span>.
            Forward only what you can defend.
          </p>

          {/* Free results → soft-lock / share-to-unlock / paid deepen */}
          {!isDeep && (
            <section className="rounded-xl border border-amber-500/30 bg-gradient-to-br from-amber-500/10 via-slate-900/80 to-emerald-500/10 p-4 sm:p-5">
              <div className="flex items-start gap-3 mb-3">
                <Sparkles className="w-5 h-5 text-amber-300 shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white font-bold text-base">
                    {canUnlockDeeper
                      ? 'You are paid — unlock deeper research on this site'
                      : softLocked
                        ? `Free preview — top ${FREE_PUNCH_VISIBLE} punch lines`
                        : 'Full free punch list unlocked'}
                  </h3>
                  <p className="text-gray-300 text-sm mt-1">
                    {canUnlockDeeper
                      ? 'Re-run with your paid email for Contractor Pro deep scout research and richer citations.'
                      : softLocked
                        ? 'Forward/share this punch list to unlock the rest for free — or upgrade for deep research + IC PDFs. Strongest citeable coverage: Dallas / Plano / Austin.'
                        : 'Upgrade for deep scout research, full cost rollups, and IC Project PDF packages.'}
                  </p>
                </div>
              </div>
              <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                {canUnlockDeeper && onUnlockDeeper ? (
                  <button
                    type="button"
                    onClick={onUnlockDeeper}
                    disabled={unlockLoading}
                    className="px-4 py-3 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm disabled:opacity-60"
                  >
                    {unlockLoading ? 'Running deep research…' : 'Unlock deeper results on this site'}
                  </button>
                ) : (
                  <>
                    {softLocked && (
                      <button
                        type="button"
                        onClick={() => void copyShareText('text')}
                        className="px-4 py-3 min-h-[48px] rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold text-sm"
                      >
                        Forward punch list — unlock full free list
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => goCheckout('contractor_pro')}
                      className="px-4 py-3 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm"
                    >
                      Contractor Pro — $149/mo
                    </button>
                    <button
                      type="button"
                      onClick={() => goCheckout('ic_project')}
                      className="px-4 py-3 min-h-[48px] rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm"
                    >
                      IC Project Report — $1,500
                    </button>
                  </>
                )}
              </div>
            </section>
          )}

          {/* Deep plan — Pro only */}
          {isDeep && analysis.pro_summary_markdown ? (
            <section className="bg-slate-800/40 border border-emerald-500/20 rounded-lg p-4">
              <h3 className="text-sm font-bold text-emerald-300 mb-2">Deep research action plan</h3>
              <pre className="whitespace-pre-wrap text-xs text-gray-300 max-h-64 overflow-y-auto font-sans">
                {analysis.pro_summary_markdown.slice(0, 6000)}
              </pre>
              {(analysis.pro_source_urls || []).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {analysis.pro_source_urls.slice(0, 6).map((url) => (
                    <a
                      key={url}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-emerald-300 underline truncate max-w-[240px]"
                    >
                      {url.replace(/^https?:\/\//, '').slice(0, 48)}
                    </a>
                  ))}
                </div>
              )}
            </section>
          ) : !isDeep ? (
            <section className="relative overflow-hidden rounded-lg border border-slate-700/60 bg-slate-800/30 p-4">
              <div className="blur-sm select-none pointer-events-none opacity-50">
                <h3 className="text-sm font-bold text-emerald-300 mb-2">Deep research action plan</h3>
                <p className="text-xs text-gray-400">
                  Contractor Pro unlocks a citeable scout action plan with AHJ source links for this site…
                </p>
              </div>
              <div className="absolute inset-0 flex items-center justify-center bg-slate-950/50">
                <button
                  type="button"
                  onClick={() => (canUnlockDeeper && onUnlockDeeper ? onUnlockDeeper() : goCheckout('contractor_pro'))}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold"
                >
                  Unlock deep action plan
                </button>
              </div>
            </section>
          ) : null}

          {/* Critical path / punch list highlights */}
          <section>
            <button
              type="button"
              onClick={() => toggle('critical')}
              className="w-full flex items-center justify-between bg-emerald-600/20 border border-emerald-500/30 rounded-lg p-4 mb-3"
            >
              <h3 className="text-lg font-bold text-white">Pre-bid punch list</h3>
              {expanded.critical ? (
                <ChevronUp className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              )}
            </button>
            {expanded.critical && (
              <div className="space-y-2">
                {(analysis.punch_list?.critical_path || []).slice(0, Math.min(5, punchVisible)).map((task, idx) => {
                  const meta = typeof task === 'string' ? { task } : task;
                  return (
                    <div key={idx} className="bg-red-900/20 border border-red-500/30 rounded-lg p-3">
                      <p className="text-gray-200 text-sm">
                        <span className="text-red-400 font-bold mr-2">{idx + 1}.</span>
                        {criticalPathTask(task)}
                      </p>
                      <CitationBadge
                        source_url={meta.source_url}
                        source_label={meta.source_label}
                        verified={meta.verified}
                        cost_verified={meta.cost_verified}
                        estimated_cost={meta.estimated_cost}
                      />
                    </div>
                  );
                })}
                {(analysis.punch_list?.punch_list || []).slice(0, punchVisible).map((item, idx) => (
                  <div key={`pl-${idx}`} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3">
                    <div className="flex justify-between gap-2 mb-1">
                      <p className="text-white text-sm font-semibold">{item.task}</p>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-semibold whitespace-nowrap ${getPriorityBadge(item.priority)}`}
                      >
                        {item.priority}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">
                      {item.timeline} • {item.responsible_party}
                      {!softLocked && item.estimated_cost != null && item.estimated_cost > 0
                        ? ` • $${item.estimated_cost.toLocaleString()}`
                        : ''}
                    </p>
                    <CitationBadge
                      source_url={item.source_url}
                      source_label={item.source_label}
                      verified={item.verified}
                      cost_verified={item.cost_verified}
                      estimated_cost={softLocked ? undefined : item.estimated_cost}
                    />
                  </div>
                ))}
                {softLocked &&
                  ((analysis.punch_list?.punch_list || []).length > FREE_PUNCH_VISIBLE ||
                    (analysis.punch_list?.critical_path || []).length > FREE_PUNCH_VISIBLE) && (
                    <div className="rounded-lg border border-dashed border-purple-500/40 bg-purple-500/10 p-4 text-center">
                      <p className="text-sm text-purple-100 mb-3">
                        {Math.max(
                          0,
                          (analysis.punch_list?.punch_list || []).length - FREE_PUNCH_VISIBLE
                        )}{' '}
                        more punch lines locked — forward this list or upgrade to unlock.
                      </p>
                      <div className="flex flex-col sm:flex-row gap-2 justify-center">
                        <button
                          type="button"
                          onClick={() => void copyShareText('text')}
                          className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-bold"
                        >
                          Forward to unlock
                        </button>
                        <button
                          type="button"
                          onClick={() => goCheckout('contractor_pro')}
                          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold"
                        >
                          Unlock with Pro
                        </button>
                      </div>
                    </div>
                  )}
              </div>
            )}
          </section>

          {/* Timeline & cost — cost rollup soft-locked for free */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-5">
              <h3 className="text-sm font-bold text-gray-400 mb-2">Timeline</h3>
              <p className="text-2xl font-black text-blue-400">
                {analysis.summary.estimated_timeline}
              </p>
              <CitationBadge verified={false} source_label="Estimate — confirm with AHJ" />
            </div>
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-5 relative overflow-hidden">
              <h3 className="text-sm font-bold text-gray-400 mb-2">Estimated Cost</h3>
              {softLocked ? (
                <>
                  <p className="text-2xl font-black text-green-400 blur-sm select-none">$••,•••</p>
                  <p className="text-xs text-amber-200/90 mt-2">
                    Full cost rollup unlocks when you forward the punch list or upgrade.
                  </p>
                  <button
                    type="button"
                    onClick={() => void copyShareText('text')}
                    className="mt-3 text-sm font-bold text-emerald-300 underline"
                  >
                    Forward to reveal estimate
                  </button>
                </>
              ) : (
                <>
                  <p className="text-2xl font-black text-green-400">
                    ${(analysis.summary.estimated_total_cost || 0).toLocaleString()}
                  </p>
                  <CitationBadge
                    verified={Boolean(analysis.punch_list?.estimates_verified)}
                    cost_verified={Boolean(analysis.punch_list?.estimates_verified)}
                    estimated_cost={analysis.summary.estimated_total_cost}
                    source_label="Rollup of line items"
                  />
                </>
              )}
            </div>
          </div>

          {/* Environmental findings */}
          <section>
            <button
              type="button"
              onClick={() => toggle('environmental')}
              className="w-full flex items-center justify-between bg-purple-600/20 border border-purple-500/30 rounded-lg p-4 mb-3"
            >
              <h3 className="text-lg font-bold text-white">Environmental Findings</h3>
              {expanded.environmental ? (
                <ChevronUp className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              )}
            </button>
            {expanded.environmental && (
              <div className="space-y-3">
                {(analysis.environmental_screening.findings || []).slice(0, findingsVisible).map((finding, idx) => (
                  <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2 gap-2">
                      <h4 className="font-bold text-white capitalize">
                        {finding.category.replace(/_/g, ' ')}
                      </h4>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-semibold ${getRiskColor(finding.risk_level)}`}
                      >
                        {finding.risk_level}
                      </span>
                    </div>
                    <p className="text-gray-300 text-sm mb-2">{finding.description}</p>
                    {(finding.action_items || []).length > 0 && (
                      <ul className="space-y-1 mb-2">
                        {finding.action_items.slice(0, 3).map((item, i) => (
                          <li key={i} className="text-xs text-gray-400 flex gap-2">
                            <span className="text-purple-400">•</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    <CitationBadge
                      data_sources={finding.data_sources}
                      verified={false}
                      source_label={(finding.data_sources || [])[0]}
                    />
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
