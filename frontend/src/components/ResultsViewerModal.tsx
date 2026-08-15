/**
 * ResultsViewerModal — full-page results panel (document scroll, not a nested modal).
 * Stays on the current page (homepage / free-trial); does not require /results navigation.
 */

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ChevronDown, ChevronUp, Copy, Check, Share2, Sparkles, Download, RefreshCw } from 'lucide-react';
import SendResultsForm, { ResultsSummaryPayload } from './SendResultsForm';
import CitationBadge from './CitationBadge';
import { backendUrl } from '../env';

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
  job_id?: string;
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
  fee_card?: {
    title?: string;
    timeline?: string;
    timeline_hint?: string;
    fees?: Array<{
      label?: string;
      amount_usd?: number | null;
      detail?: string;
      verified?: boolean;
      planning_aid?: boolean;
      source_url?: string | null;
      source_label?: string | null;
    }>;
    citeable_coverage?: boolean;
    disclaimer?: string;
    planning_aid?: boolean;
    paid_local_confirm?: boolean;
  };
  ahj_card?: {
    title?: string;
    name?: string;
    portal_url?: string;
    fees_url?: string;
    phone?: string;
    notes?: string;
    citeable_coverage?: boolean;
  };
  gotcha_watchlist?: {
    title?: string;
    items?: Array<{
      id?: string;
      title?: string;
      detail?: string;
      priority?: string;
      source_url?: string | null;
      source_label?: string | null;
    }>;
    citeable_coverage?: boolean;
  };
  document_checklist?: {
    title?: string;
    items?: Array<{ task?: string; done?: boolean }>;
    disclaimer?: string;
  };
  contingency_band?: {
    label?: string;
    pct_low?: number;
    pct_mid?: number;
    pct_high?: number;
    usd_mid?: number | null;
    disclaimer?: string;
    drivers?: { critical_items?: number; high_items?: number; unverified_items?: number };
  };
  /** Premortem honesty: full_pack | portal_seed | federal_state */
  coverage?: {
    tier?: string;
    badge?: string;
    badge_short?: string;
    tone?: string;
    warning?: string;
    note?: string;
    pack_key?: string | null;
    state_citeable?: boolean;
    fees_allowed?: boolean;
    depth_equals_beachhead?: boolean;
  };
  jurisdiction?: {
    zip?: string;
    city?: string;
    state?: string;
    county?: string;
    citeable_local?: boolean;
    portal_only_local?: boolean;
    coverage_tier?: string;
    coverage_badge?: string;
    coverage_note?: string;
    local_pack_key?: string;
  };
  free_confirm?: {
    pack_key?: string;
    citeable?: boolean;
    portal_only?: boolean;
    coverage_note?: string;
  };
  finops_mode?: string;
  paid_local?: {
    status?: string;
    reason?: string;
    user_message?: string;
    fee_rows_extracted?: number;
    pages_scraped?: number;
    pages_cap?: number;
    cache_hit?: boolean;
    method?: string;
  };
  paid_local_quota?: {
    used?: number;
    limit?: number;
    remaining?: number;
    capped?: boolean;
    email?: string;
  };
  /** Top 3 margin killers for Bid Risk Receipt / share text */
  margin_killers?: Array<{
    title?: string;
    detail?: string;
    kind?: string;
    priority?: string;
    verified?: boolean;
    source_url?: string | null;
    source_label?: string | null;
    planning_exposure?: {
      label?: string;
      usd_low?: number;
      usd_mid?: number;
      usd_high?: number;
      basis?: string;
      verified?: boolean;
      disclaimer?: string;
    };
  }>;
  planning_exposure_summary?: {
    label?: string;
    usd_mid_total?: number | null;
    killer_count?: number;
    verified?: boolean;
    disclaimer?: string;
    data_center_mode?: boolean;
  };
  dc_positioning?: {
    headline?: string;
    pitch?: string;
    buyer?: string;
  };
  recheck_diff?: {
    change_count?: number;
    changes?: string[];
  };
}

function criticalPathTask(item: CriticalPathItem): string {
  return typeof item === 'string' ? item : item.task;
}

function resolveCoverage(view: AnalysisData): {
  tier: string;
  badge: string;
  warning: string;
  note: string;
  feesAllowed: boolean;
} {
  const c = view.coverage;
  if (c?.tier === 'paid_local') {
    return {
      tier: 'paid_local',
      badge: c.badge || 'Paid local confirm',
      warning:
        c.warning ||
        'Page-capped · cached · not a full city pack. Fee dollars are planning aids — confirm on the official AHJ schedule.',
      note: c.note || '',
      feesAllowed: true,
    };
  }
  if (c?.tier && c.badge) {
    return {
      tier: c.tier,
      badge: c.badge,
      warning: c.warning || '',
      note: c.note || c.warning || '',
      feesAllowed: Boolean(c.fees_allowed ?? c.tier === 'full_pack'),
    };
  }
  const j = view.jurisdiction;
  if (j?.citeable_local) {
    return {
      tier: 'full_pack',
      badge: 'Full city pack',
      warning: 'Curated local fees/gotchas — still confirm dollars on the official schedule.',
      note: j.coverage_note || '',
      feesAllowed: true,
    };
  }
  if (j?.portal_only_local || view.free_confirm?.portal_only) {
    return {
      tier: 'portal_seed',
      badge: 'Portal seed — confirm fees',
      warning:
        'AHJ portal link only — not full-pack depth. No curated local fees or ordinance gotchas.',
      note: j?.coverage_note || view.free_confirm?.coverage_note || '',
      feesAllowed: false,
    };
  }
  return {
    tier: 'federal_state',
    badge: 'Federal / state only',
    warning:
      'No curated local AHJ pack. Federal (+ state when curated) only — confirm local requirements with the AHJ.',
    note: j?.coverage_note || view.free_confirm?.coverage_note || '',
    feesAllowed: false,
  };
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

function freeRunUrl(): string {
  try {
    const ref =
      sessionStorage.getItem('affiliateCode') ||
      sessionStorage.getItem('referralCode') ||
      localStorage.getItem('referralCode');
    if (ref) return `${APP_URL}?ref=${encodeURIComponent(ref)}&utm_source=bid_receipt`;
  } catch {
    /* ignore */
  }
  return `${APP_URL}?utm_source=bid_receipt`;
}

/** SMS/chat-forwardable receipt — short, CYA, not an ad. */
function buildShareText(analysis: AnalysisData, generatedFor?: string): string {
  const p = analysis.project_info;
  const ahj = analysis.ahj_card?.name || 'Local AHJ';
  const band = analysis.contingency_band;
  const killers =
    analysis.margin_killers && analysis.margin_killers.length > 0
      ? analysis.margin_killers
      : (analysis.punch_list?.critical_path || []).slice(0, 3).map((t) => ({
          title: typeof t === 'string' ? t : t.task,
          detail: '',
          priority: 'HIGH',
          verified: false,
        }));

  const bandLine =
    band?.pct_low != null && band?.pct_high != null
      ? `Contingency: +${band.pct_low}% to +${band.pct_high}% (mid ${band.pct_mid}%) — planning aid, NOT a quote`
      : `Confirm contingency with AHJ before bid`;

  const killerLines = killers
    .slice(0, 3)
    .map((k, i) => {
      const ver = k.verified && k.source_url ? 'Source' : 'Unverified';
      const pri = (k.priority || 'NOTE').toUpperCase();
      const title = (k.title || 'Item').slice(0, 90);
      return `${i + 1}. [${pri}] [${ver}] ${title}`;
    })
    .join('\n');

  const who = (generatedFor || '').trim() || 'Estimator';
  const isDc = Boolean(
    analysis.dc_positioning ||
      analysis.planning_exposure_summary?.data_center_mode ||
      /data.?center|colo/i.test(analysis.project_info?.type || '')
  );
  const cov = resolveCoverage(analysis);

  return [
    `FLAGGED BEFORE BID — ${p.address}, ${p.city}, ${p.state} ${p.zip}`,
    `Coverage: ${cov.badge}`,
    `AHJ: ${ahj}`,
    bandLine,
    killerLines ? `Top 3 risk flags:\n${killerLines}` : '',
    isDc ? 'Note: AHJ + utility often run parallel (not an interconnect study).' : '',
    `— ${who} · Reg Guard Bid Risk Receipt`,
    `Planning aid only. Confirm with AHJ. Not a filing.`,
    `Own site: ${freeRunUrl()}`,
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
  const [packetLoading, setPacketLoading] = useState(false);
  const [recheckLoading, setRecheckLoading] = useState(false);
  const [liveAnalysis, setLiveAnalysis] = useState<AnalysisData | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  // Page-scroll takeover: bring results to the top of the viewport (form scrolls away)
  useEffect(() => {
    if (!isOpen) return;
    const id = window.requestAnimationFrame(() => {
      const el = rootRef.current;
      if (!el) return;
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // Standalone / iOS PWA: also pin window scroll in case scrollIntoView is ignored
      const top = el.getBoundingClientRect().top + window.scrollY - 8;
      window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    });
    return () => window.cancelAnimationFrame(id);
  }, [isOpen, analysis]);

  useEffect(() => {
    setLiveAnalysis(null);
  }, [analysis]);

  if (!isOpen || !analysis) return null;

  const view = liveAnalysis || analysis;
  const coverage = resolveCoverage(view);

  const summary = buildSummaryFromAnalysis(view);
  const effectiveResearchId = researchId || view.research_id || null;
  const emailForCheckout = (defaultEmail || sessionStorage.getItem('userEmail') || '')
    .trim()
    .toLowerCase();
  const shareText = buildShareText(view, emailForCheckout);
  const depth = (view.research_depth || '').toLowerCase();
  const isDeep = depth === 'pro' || depth === 'pro_partial';
  // Soft-lock: free sees limited lines unless they shared OR paid deep research
  const softLocked = !isDeep && !shareUnlocked;
  const punchVisible = softLocked ? FREE_PUNCH_VISIBLE : 50;
  const findingsVisible = softLocked ? FREE_FINDINGS_VISIBLE : 12;

  const downloadBidReceipt = async () => {
    setPacketLoading(true);
    try {
      const res = await fetch(backendUrl('/bid-receipt/pdf'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_data: view,
          generated_for: emailForCheckout || undefined,
          share_url: freeRunUrl(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Bid Risk Receipt failed');
      if (data.download_url) {
        window.open(data.download_url, '_blank', 'noopener,noreferrer');
        setToast('Bid Risk Receipt PDF ready — forward it');
        try {
          sessionStorage.setItem('shareUnlocked', '1');
        } catch {
          /* ignore */
        }
        setShareUnlocked(true);
      }
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Bid Risk Receipt failed');
    } finally {
      setPacketLoading(false);
      window.setTimeout(() => setToast(''), 3500);
    }
  };

  const downloadBidPacketFull = async () => {
    setPacketLoading(true);
    try {
      const res = await fetch(backendUrl('/bid-packet/pdf'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis_data: view, mode: 'full' }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Bid packet failed');
      if (data.download_url) {
        window.open(data.download_url, '_blank', 'noopener,noreferrer');
        setToast('Full bid packet PDF ready');
      }
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Bid packet failed');
    } finally {
      setPacketLoading(false);
      window.setTimeout(() => setToast(''), 3500);
    }
  };

  const runRecheck = async () => {
    const jobId = view.job_id || sessionStorage.getItem('lastJobId') || '';
    if (!jobId || !emailForCheckout) {
      setToast('Save a lookup with your email first, then re-check from Saved Jobs.');
      window.setTimeout(() => setToast(''), 4000);
      return;
    }
    setRecheckLoading(true);
    try {
      const res = await fetch(backendUrl(`/jobs/${jobId}/recheck`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner_email: emailForCheckout }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Recheck failed');
      const next = (data.analysis_data || {}) as AnalysisData;
      next.job_id = jobId;
      next.recheck_diff = data.diff;
      setLiveAnalysis(next);
      setToast(
        data.diff?.change_count
          ? `Recheck: ${data.diff.change_count} change(s) since last run`
          : 'Recheck complete — no material changes detected'
      );
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Recheck failed');
    } finally {
      setRecheckLoading(false);
      window.setTimeout(() => setToast(''), 4500);
    }
  };

  const paidTierHint = (
    (typeof window !== 'undefined' && sessionStorage.getItem('regguardTier')) ||
    ''
  ).toLowerCase();
  const isPartnerTier = paidTierHint === 'partner';

  const goCheckout = (tier: 'partner' | 'contractor_pro' | 'ic_project') => {
    // Persist site so return after payment can deepen the same lookup
    try {
      const pi = view.project_info;
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
    setToast('Full free punch list unlocked — forward the Bid Risk Receipt next.');
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
      ref={rootRef}
      id="results-viewer"
      className="w-full scroll-mt-3"
      role="region"
      aria-labelledby="results-modal-title"
    >
      <div className="w-full flex flex-col bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-purple-500/30 rounded-2xl shadow-2xl">
        {/* Header — scrolls away with the page (not a frozen overlay) */}
        <div className="flex items-start justify-between gap-4 px-5 sm:px-8 py-5 border-b border-slate-700/80 bg-slate-900/90">
          <div>
            <h2 id="results-modal-title" className="text-2xl sm:text-3xl font-black text-white">
              Your Site Diligence Analysis
            </h2>
            <p className="text-gray-400 text-sm mt-1">
              {view.project_info.address} • {view.project_info.city},{' '}
              {view.project_info.state} {view.project_info.zip}
            </p>
            {(view.research_depth === 'pro' || view.research_depth === 'pro_partial') && (
              <p className="mt-2 inline-flex items-center px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                {view.research_depth === 'pro'
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

        {/* Text / Email + social share — scrolls with results (page scroll) */}
        <div className="px-5 sm:px-8 py-4 border-b border-emerald-500/30 bg-slate-950/90 space-y-3">
          <SendResultsForm
            researchId={effectiveResearchId}
            summary={summary}
            defaultEmail={defaultEmail}
            defaultPhone={defaultPhone}
          />

          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-emerald-300/90 mb-2 flex items-center gap-2">
              <Share2 className="w-3.5 h-3.5" />
              Share Bid Risk Receipt
            </p>
            <p className="text-xs text-gray-400 mb-2">
              Default share object: contingency band + top 3 margin killers + free-run CTA.
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void downloadBidReceipt()}
                disabled={packetLoading}
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold disabled:opacity-50"
              >
                <Download className="w-4 h-4" />
                {packetLoading ? 'Building…' : 'Download Receipt PDF'}
              </button>
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
                {copied === 'text' ? 'Copied receipt' : 'Copy receipt'}
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

        {/* Results body — page scroll (no nested overflow panel) */}
        <div className="px-5 sm:px-8 py-6 space-y-6">
          <p className="text-xs text-gray-400">
            Every line shows a source link or <span className="text-amber-300 font-semibold">Unverified</span>.
            Forward only what you can defend.
          </p>

          {/* Bid Risk Receipt — first in results (forwardable hero) */}
          {(view.contingency_band || (view.margin_killers && view.margin_killers.length > 0)) && (
            <section className="rounded-xl border border-emerald-500/40 bg-emerald-500/5 p-4 sm:p-5">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-emerald-300">
                    Flagged before bid day
                  </p>
                  <h3 className="text-lg font-bold text-white mt-0.5">
                    Bid Risk Receipt — forward to GC / owner
                  </h3>
                  <p className="text-gray-400 text-sm mt-1">
                    Site-specific CYA stamp: big contingency + 3 risk flags. Planning aid —
                    not a quote, not a filing.
                    {view.dc_positioning ? ' Parallel AHJ + utility clocks.' : ''}
                  </p>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => void copyShareText('text')}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold"
                  >
                    <Copy className="w-4 h-4" />
                    Copy forward text
                  </button>
                  <button
                    type="button"
                    onClick={() => void downloadBidReceipt()}
                    disabled={packetLoading}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg bg-white/10 border border-emerald-500/40 text-white text-sm font-semibold disabled:opacity-50"
                  >
                    <Download className="w-4 h-4" />
                    {packetLoading ? 'Building…' : 'PDF for thread'}
                  </button>
                </div>
              </div>
              <p className="text-xs text-gray-400 mb-2">
                {view.project_info.address} · {view.ahj_card?.name || 'Local AHJ'}
              </p>
              {view.contingency_band && (
                <p className="text-4xl font-black text-emerald-400 mb-1 tracking-tight">
                  +{view.contingency_band.pct_low}% – +{view.contingency_band.pct_high}%
                </p>
              )}
              {view.contingency_band && (
                <p className="text-sm text-gray-300 mb-3">
                  mid {view.contingency_band.pct_mid}% · planning aid — not a quote
                </p>
              )}
              <ol className="space-y-2 list-decimal pl-5">
                {(view.margin_killers || []).slice(0, 3).map((k, i) => (
                  <li key={`${k.title}-${i}`} className="text-sm text-gray-200">
                    <span className="text-amber-200 font-semibold text-xs uppercase mr-1">
                      {k.priority || 'NOTE'}
                    </span>
                    <span className="text-white font-medium">{k.title}</span>
                    {k.detail && (
                      <p className="text-gray-400 text-xs mt-0.5 line-clamp-2">{k.detail}</p>
                    )}
                    {k.planning_exposure?.usd_mid != null && (
                      <p className="text-emerald-300/90 text-xs mt-1">
                        Planning exposure ~$
                        {Number(k.planning_exposure.usd_low || 0).toLocaleString()}–$
                        {Number(k.planning_exposure.usd_high || 0).toLocaleString()} — not
                        guaranteed savings
                      </p>
                    )}
                    <CitationBadge
                      verified={Boolean(k.verified && k.source_url)}
                      source_url={k.source_url}
                      source_label={k.source_label || 'Unverified'}
                    />
                  </li>
                ))}
              </ol>
              <p className="text-xs text-gray-500 mt-3 border-t border-emerald-500/20 pt-2">
                Stamp: {emailForCheckout || 'Estimator'} · Confirm with AHJ · Not a filing ·{' '}
                <button
                  type="button"
                  onClick={openWhatsApp}
                  className="text-emerald-300 underline font-semibold"
                >
                  WhatsApp forward
                </button>
              </p>
            </section>
          )}

          {/* Coverage honesty badge — premortem P1/P5/P7 */}
          <section
            className={`rounded-xl border p-4 ${
              coverage.tier === 'full_pack' || coverage.tier === 'paid_local'
                ? 'border-emerald-500/40 bg-emerald-500/10'
                : coverage.tier === 'portal_seed'
                  ? 'border-amber-500/40 bg-amber-500/10'
                  : 'border-slate-600 bg-slate-800/60'
            }`}
            aria-label="Coverage depth"
          >
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span
                className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold tracking-wide ${
                  coverage.tier === 'full_pack' || coverage.tier === 'paid_local'
                    ? 'bg-emerald-600 text-white'
                    : coverage.tier === 'portal_seed'
                      ? 'bg-amber-600 text-white'
                      : 'bg-slate-600 text-gray-100'
                }`}
              >
                {coverage.badge}
              </span>
              {coverage.tier !== 'full_pack' && coverage.tier !== 'paid_local' && (
                <span className="text-xs text-amber-200/90 font-semibold">
                  Not the same depth as a full city pack
                </span>
              )}
              {coverage.tier === 'paid_local' && (
                <span className="text-xs text-emerald-200/90 font-semibold">
                  Page-capped · cached · not a full city pack
                </span>
              )}
            </div>
            <p className="text-sm text-gray-200">{coverage.warning}</p>
            {coverage.note && coverage.note !== coverage.warning && (
              <p className="text-xs text-gray-400 mt-2">{coverage.note}</p>
            )}
            {view.paid_local?.status === 'capped' && (
              <p className="text-sm text-amber-200 mt-3" role="status">
                {view.paid_local.user_message ||
                  'Daily paid scrape cap reached. Showing federal/state + pack/cache. Try again tomorrow or use an IC Project for heavy research.'}
              </p>
            )}
            {view.paid_local_quota && typeof view.paid_local_quota.limit === 'number' && view.paid_local_quota.limit > 0 && (
              <p className="text-xs text-gray-400 mt-2">
                Paid scrape quota today:{' '}
                <span className="text-gray-200 font-semibold">
                  {view.paid_local_quota.used ?? 0}/{view.paid_local_quota.limit}
                </span>
                {typeof view.paid_local_quota.remaining === 'number'
                  ? ` · ${view.paid_local_quota.remaining} remaining`
                  : ''}
              </p>
            )}
          </section>

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
                        ? 'Forward this Bid Risk Receipt to unlock the rest for free — or upgrade for deep research + IC PDFs.'
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
                        onClick={() => void downloadBidReceipt()}
                        disabled={packetLoading}
                        className="px-4 py-3 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm disabled:opacity-60"
                      >
                        {packetLoading ? 'Building receipt…' : 'Forward Bid Risk Receipt — unlock full free list'}
                      </button>
                    )}
                    {softLocked && (
                      <button
                        type="button"
                        onClick={() => void copyShareText('text')}
                        className="px-4 py-3 min-h-[48px] rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold text-sm"
                      >
                        Copy receipt text
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => goCheckout('partner')}
                      className="px-4 py-3 min-h-[48px] rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-bold text-sm"
                    >
                      Partner — $79/mo
                    </button>
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

          {/* Partner → Pro upgrade */}
          {isDeep && isPartnerTier && (
            <section className="rounded-xl border border-teal-500/30 bg-teal-500/10 p-4">
              <h3 className="text-white font-bold text-sm mb-1">On Partner — need more for your own bids?</h3>
              <p className="text-gray-300 text-sm mb-3">
                Upgrade to Contractor Pro ($149/mo) for unlimited deep lookups on your bid week sites.
              </p>
              <button
                type="button"
                onClick={() => goCheckout('contractor_pro')}
                className="px-4 py-3 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm"
              >
                Upgrade to Contractor Pro
              </button>
            </section>
          )}

          {/* IC attach on deep jobs */}
          {isDeep && !isPartnerTier && (
            <section className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-4">
              <h3 className="text-white font-bold text-sm mb-1">Need PDFs for this site?</h3>
              <p className="text-gray-300 text-sm mb-3">
                IC Project Report ($1,500): research memo + punch list + permit worksheet PDFs.
                Planning diligence — not an official AHJ filing. Coverage depth is labeled on this receipt.
              </p>
              <button
                type="button"
                onClick={() => goCheckout('ic_project')}
                className="px-4 py-3 min-h-[48px] rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm"
              >
                Get IC Project Report
              </button>
            </section>
          )}

          {/* Deep plan — Pro only */}
          {isDeep && view.pro_summary_markdown ? (
            <section className="bg-slate-800/40 border border-emerald-500/20 rounded-lg p-4">
              <h3 className="text-sm font-bold text-emerald-300 mb-2">Deep research action plan</h3>
              <pre className="whitespace-pre-wrap text-xs text-gray-300 max-h-64 overflow-y-auto font-sans">
                {view.pro_summary_markdown.slice(0, 6000)}
              </pre>
              {(view.pro_source_urls || []).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {view.pro_source_urls.slice(0, 6).map((url) => (
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
                <p className="text-xs text-gray-400 px-1 pb-1">
                  Coverage: <span className="text-gray-200 font-semibold">{coverage.badge}</span>
                  {!coverage.feesAllowed
                    ? ' — fee dollars not shown; open the AHJ portal to confirm.'
                    : ' — confirm fee dollars on the official schedule.'}
                </p>
                {(view.punch_list?.critical_path || []).slice(0, Math.min(5, punchVisible)).map((task, idx) => {
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
                {(view.punch_list?.punch_list || []).slice(0, punchVisible).map((item, idx) => (
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
                  ((view.punch_list?.punch_list || []).length > FREE_PUNCH_VISIBLE ||
                    (view.punch_list?.critical_path || []).length > FREE_PUNCH_VISIBLE) && (
                    <div className="rounded-lg border border-dashed border-purple-500/40 bg-purple-500/10 p-4 text-center">
                      <p className="text-sm text-purple-100 mb-3">
                        {Math.max(
                          0,
                          (view.punch_list?.punch_list || []).length - FREE_PUNCH_VISIBLE
                        )}{' '}
                        more punch lines locked — forward the Bid Risk Receipt or upgrade to unlock.
                      </p>
                      <div className="flex flex-col sm:flex-row gap-2 justify-center">
                        <button
                          type="button"
                          onClick={() => void downloadBidReceipt()}
                          disabled={packetLoading}
                          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold disabled:opacity-60"
                        >
                          {packetLoading ? 'Building…' : 'Export Receipt — unlock'}
                        </button>
                        <button
                          type="button"
                          onClick={() => void copyShareText('text')}
                          className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-bold"
                        >
                          Copy receipt text
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
                {view.summary.estimated_timeline}
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
                    ${(view.summary.estimated_total_cost || 0).toLocaleString()}
                  </p>
                  <CitationBadge
                    verified={Boolean(view.punch_list?.estimates_verified)}
                    cost_verified={Boolean(view.punch_list?.estimates_verified)}
                    estimated_cost={view.summary.estimated_total_cost}
                    source_label="Rollup of line items"
                  />
                </>
              )}
            </div>
          </div>

          {/* Bid-time arbitrage layer */}
          {(view.fee_card || view.ahj_card || view.gotcha_watchlist || view.contingency_band) && (
            <section className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <h3 className="text-lg font-bold text-white">Bid-time arbitrage</h3>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void downloadBidReceipt()}
                    disabled={packetLoading}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold disabled:opacity-50 min-h-[44px]"
                  >
                    <Download className="w-4 h-4" />
                    {packetLoading ? 'Building…' : 'Export Receipt PDF'}
                  </button>
                  <button
                    type="button"
                    onClick={() => void downloadBidPacketFull()}
                    disabled={packetLoading}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 border border-slate-500/50 text-white text-sm font-semibold disabled:opacity-50 min-h-[44px]"
                  >
                    Full packet
                  </button>
                  <button
                    type="button"
                    onClick={() => void runRecheck()}
                    disabled={recheckLoading}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 border border-purple-400/40 text-white text-sm font-bold disabled:opacity-50 min-h-[44px]"
                  >
                    <RefreshCw className="w-4 h-4" />
                    {recheckLoading ? 'Re-checking…' : 'Re-check site'}
                  </button>
                </div>
              </div>

              {view.recheck_diff && (view.recheck_diff.change_count || 0) > 0 && (
                <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-100">
                  <p className="font-bold mb-1">
                    {view.recheck_diff.change_count} change(s) since last run
                  </p>
                  <ul className="list-disc pl-5 space-y-1">
                    {(view.recheck_diff.changes || []).slice(0, 8).map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              {view.ahj_card && (
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
                  <h4 className="text-sm font-bold text-emerald-300 mb-2">
                    {view.ahj_card.title || 'AHJ portal & contact'}
                  </h4>
                  <p className="text-white font-semibold">{view.ahj_card.name}</p>
                  {view.ahj_card.portal_url && (
                    <a
                      href={view.ahj_card.portal_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-purple-300 underline block mt-1"
                    >
                      Open AHJ portal
                    </a>
                  )}
                  {view.ahj_card.fees_url && (
                    <a
                      href={view.ahj_card.fees_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-purple-300 underline block"
                    >
                      Fee schedule
                    </a>
                  )}
                  {view.ahj_card.notes && (
                    <p className="text-gray-400 text-xs mt-2">{view.ahj_card.notes}</p>
                  )}
                </div>
              )}

              {view.fee_card && (
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
                  <h4 className="text-sm font-bold text-blue-300 mb-2">
                    {view.fee_card.title || 'Fee & timeline extract'}
                    {(view.fee_card.planning_aid || view.fee_card.paid_local_confirm) && (
                      <span className="ml-2 text-xs font-semibold text-amber-300">
                        Planning aid
                      </span>
                    )}
                  </h4>
                  <p className="text-white text-sm mb-2">
                    Timeline: {view.fee_card.timeline || view.summary.estimated_timeline}
                  </p>
                  {!coverage.feesAllowed ? (
                    <p className="text-amber-200/90 text-sm">
                      Dollar fees not shown for {coverage.badge.toLowerCase()} coverage. Use{' '}
                      {view.ahj_card?.fees_url || view.ahj_card?.portal_url ? (
                        <a
                          href={view.ahj_card.fees_url || view.ahj_card.portal_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="underline text-purple-300"
                        >
                          the AHJ portal
                        </a>
                      ) : (
                        'the AHJ portal'
                      )}{' '}
                      to confirm the official schedule before bid.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {(view.fee_card.fees || []).slice(0, 6).map((f, i) => (
                        <li key={i} className="text-sm text-gray-300">
                          <span className="text-white font-medium">{f.label}</span>
                          {typeof f.amount_usd === 'number'
                            ? ` — $${f.amount_usd.toLocaleString()}`
                            : ''}
                          {(f.planning_aid ||
                            view.fee_card?.planning_aid ||
                            view.fee_card?.paid_local_confirm) && (
                            <span className="ml-1 text-xs text-amber-300/90">(planning aid)</span>
                          )}
                          <CitationBadge
                            verified={Boolean(f.verified)}
                            source_url={f.source_url}
                            source_label={f.source_label || 'Confirm with AHJ'}
                          />
                        </li>
                      ))}
                    </ul>
                  )}
                  {(view.fee_card.disclaimer ||
                    view.fee_card.paid_local_confirm ||
                    view.fee_card.planning_aid) && (
                    <p className="text-amber-200/80 text-xs mt-2">
                      {view.fee_card.disclaimer ||
                        'Planning aid only — not an AHJ quote. Confirm on the official fee schedule before bid.'}
                    </p>
                  )}
                </div>
              )}

              {view.gotcha_watchlist && (view.gotcha_watchlist.items || []).length > 0 && (
                <div className="bg-slate-800/40 border border-amber-500/30 rounded-lg p-4">
                  <h4 className="text-sm font-bold text-amber-300 mb-2">
                    {view.gotcha_watchlist.title || 'Local gotcha watchlist'}
                  </h4>
                  <ul className="space-y-2">
                    {(view.gotcha_watchlist.items || []).map((g) => (
                      <li key={g.id || g.title} className="text-sm text-gray-300">
                        <span className="text-amber-200 font-semibold">{g.priority}</span>{' '}
                        <span className="text-white font-medium">{g.title}</span>
                        <p className="text-gray-400 text-xs mt-0.5">{g.detail}</p>
                        <CitationBadge
                          verified={Boolean(g.source_url)}
                          source_url={g.source_url}
                          source_label={g.source_label || 'Unverified'}
                        />
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {view.document_checklist && (
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
                  <h4 className="text-sm font-bold text-purple-300 mb-2">
                    {view.document_checklist.title || 'Document checklist'}
                  </h4>
                  <ul className="space-y-1">
                    {(view.document_checklist.items || []).map((d, i) => (
                      <li key={i} className="text-sm text-gray-300">
                        [ ] {d.task}
                      </li>
                    ))}
                  </ul>
                  {view.document_checklist.disclaimer && (
                    <p className="text-gray-500 text-xs mt-2">{view.document_checklist.disclaimer}</p>
                  )}
                </div>
              )}

              {view.contingency_band && (
                <div className="bg-slate-800/40 border border-emerald-500/30 rounded-lg p-4">
                  <h4 className="text-sm font-bold text-emerald-300 mb-2">
                    {view.contingency_band.label || 'Suggested contingency'}
                  </h4>
                  <p className="text-2xl font-black text-emerald-400">
                    {view.contingency_band.pct_low}% – {view.contingency_band.pct_high}%
                    <span className="text-base font-semibold text-gray-300 ml-2">
                      (mid {view.contingency_band.pct_mid}%)
                    </span>
                  </p>
                  {typeof view.contingency_band.usd_mid === 'number' && !softLocked && (
                    <p className="text-sm text-gray-300 mt-1">
                      ~${view.contingency_band.usd_mid.toLocaleString()} mid band on current rollup
                    </p>
                  )}
                  <p className="text-gray-500 text-xs mt-2">{view.contingency_band.disclaimer}</p>
                  <CitationBadge verified={false} source_label="Heuristic — not a quote" />
                </div>
              )}
            </section>
          )}

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
                {(view.environmental_screening.findings || []).slice(0, findingsVisible).map((finding, idx) => (
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
