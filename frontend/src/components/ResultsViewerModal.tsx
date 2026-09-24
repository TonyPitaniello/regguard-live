/**
 * ResultsViewerModal — full-page results panel (document scroll, not a nested modal).
 * Stays on the current page (homepage / free-trial); does not require /results navigation.
 */

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ChevronDown, ChevronUp, Copy, Check, Share2, Sparkles, Download, RefreshCw, MessageSquare } from 'lucide-react';
import SendResultsForm, { ResultsSummaryPayload } from './SendResultsForm';
import CitationBadge from './CitationBadge';
import { backendUrl } from '../env';
import { trackStampEvent } from '../lib/trackStampEvent';
import { rememberReferralCode, storedReferralCode, withShareParams } from '../shareLinks';
import { persistLastResearchForm, setPendingIcReport } from '../icSiteBind';
import { classifyFeeKind, feeKindHint } from '../feeKind';
import { analysisForPdfExport, artifactDownloadFilename, postBinaryDownload, postPdfDownload } from '../pdfExport';
import { downloadOnlyBlob } from '../openAndDownload';
import {
  buildArtifactTextMessage,
  copyText,
  downloadTextFile,
  textResultsToOthers,
} from '../forwardArtifacts';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';
import { IcDiligenceBundlePitch } from './IcDiligenceBundlePitch';
import { HABIT_TIERS, proDeskGateMessage, type ProDeskArtifact } from '../habitDeliverableLadder';
import { resolveResultsLadder } from '../resultsAccessLadder';

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
  citation_tier?: string | null;
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
  share_url?: string;
  preview?: boolean;
  research_depth?: string;
  depth_tier?: string;
  depth_badge?: string;
  depth_claim_note?: string;
  depth_claim_honest?: boolean;
  research_incomplete?: boolean;
  /** Labeled sample ladder: free | partner | pro — drives blur / unlock in ResultsViewerModal */
  sample_demo_tier?: 'free' | 'partner' | 'pro' | string;
  scout_mode?: string;
  scout_locality_depth?: string;
  ultralocal_scout?: { enabled?: boolean; hit_count?: number } | null;
  ic_package?: boolean | Record<string, unknown>;
  /** Set when IC Project PDFs were just generated for this lookup */
  ic_pdfs_ready?: boolean;
  local_pack?: {
    tier?: string;
    citeable?: boolean;
    promote_candidate?: boolean;
    city?: string;
    state?: string;
    zip?: string;
    ahj?: { name?: string; portal_url?: string; fees_url?: string };
    fees?: unknown[];
    gotchas?: unknown[];
  };
  honesty?: {
    risk_verified?: boolean;
    cost_verified?: boolean;
    timeline_verified?: boolean;
    source?: string;
    labels?: Record<string, string>;
  };
  upgrade_offer?: {
    message?: string;
    detail?: string;
    cta_label?: string;
    cta_tier?: string;
    secondary_cta_label?: string | null;
    secondary_cta_tier?: string | null;
    current_label?: string;
    next_label?: string | null;
    primary_once?: boolean;
    honesty_note?: string;
  };
  pro_delta?: {
    title?: string;
    bullets?: string[];
    pages_scraped?: number;
    fee_rows?: number;
    scout_sources?: number;
    verified_punch_lines?: number;
    scout_mode?: string;
    honesty?: string;
  };
  buyer_persona?: string;
  pro_summary_markdown?: string;
  pro_source_urls?: string[];
  job_id?: string;
  project_info?: {
    address: string;
    city: string;
    state: string;
    zip: string;
    type: string;
    coordinates?: { latitude: number; longitude: number };
  };
  environmental_screening?: {
    risk_level: string;
    findings: Array<{
      category: string;
      risk_level: string;
      description: string;
      action_items: string[];
      data_sources: string[];
      research_cost_usd: number;
      verified?: boolean;
      source_url?: string | null;
      source_label?: string | null;
    }>;
    total_research_cost: number;
    action_plan: string[];
    risk_honesty_note?: string;
  };
  punch_list?: {
    punch_list: PunchListItemData[];
    timeline_summary: string;
    estimated_total_cost: number;
    critical_path: CriticalPathItem[];
    milestones: Array<{ week: string; milestone: string }>;
    who_to_call: Record<string, string>;
    estimates_verified?: boolean;
  };
  summary?: {
    total_environmental_risks: number;
    high_risk_count: number;
    total_punch_list_items: number;
    estimated_timeline: string;
    estimated_total_cost: number;
  };
  next_steps?: string[];
  fee_card?: {
    title?: string;
    timeline?: string;
    timeline_hint?: string;
    fees?: Array<{
      label?: string;
      amount_usd?: number | null;
      trade?: string;
      detail?: string;
      verified?: boolean;
      planning_aid?: boolean;
      amount_requires_schedule?: boolean;
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
    apply_url?: string;
    inspections_url?: string;
    phone?: string;
    notes?: string;
    citeable_coverage?: boolean;
    last_verified?: string;
  };
  inspection_sequence_card?: {
    title?: string;
    steps?: string[];
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
      checklist?: string[];
      anti_patterns?: string[];
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
    citation_tier?: string;
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
    parallel_clocks?: boolean;
  };
  vertical_playbook?: {
    id?: string;
    label?: string;
    depth?: string;
    disclaimer?: string;
    beachhead_hint?: string;
    stats?: {
      total?: number;
      cited?: number;
      confirm?: number;
      completeness?: number;
      completeness_pct?: number;
    };
    items?: Array<{
      id?: string;
      track?: string;
      priority?: string;
      task?: string;
      status?: string;
      detail?: string;
      source_url?: string | null;
      source_label?: string | null;
      verified?: boolean;
    }>;
  };
  parallel_clocks?: {
    title?: string;
    headline?: string;
    clocks?: Array<{
      track?: string;
      label?: string;
      owner?: string;
      status?: string;
      url?: string;
    }>;
    disclaimer?: string;
  };
  moratorium_radar?: {
    title?: string;
    headline?: string;
    high_alert_state?: boolean;
    state?: string;
    metros?: Array<{
      metro?: string;
      state?: string;
      status?: string;
      summary?: string;
      citation_url?: string;
    }>;
    scout_hits?: Array<{ title?: string; url?: string; snippet?: string }>;
    bill_notes?: string[];
    disclaimer?: string;
    updated?: string;
    age_days?: number | null;
    is_stale?: boolean;
    stale_banner?: string;
    high_alert_suppressed_stale?: boolean;
  };
  power_path_card?: {
    title?: string;
    headline?: string;
    mw_hint?: number | null;
    fast41_candidate?: boolean;
    checklist?: string[];
    disclaimer?: string;
  };
  water_cooling_card?: {
    title?: string;
    headline?: string;
    water_hits?: Array<{ title?: string; url?: string; snippet?: string }>;
    wue_hits?: Array<{ title?: string; url?: string; snippet?: string }>;
    checklist?: string[];
    disclaimer?: string;
  };
  opposition_card?: {
    title?: string;
    headline?: string;
    band?: string;
    score?: number;
    score_max?: number;
    hot_signals?: Array<{
      id?: string;
      label?: string;
      level?: number;
      detail?: string;
      source_url?: string | null;
    }>;
    disclaimer?: string;
  };
  fast41_card?: {
    title?: string;
    headline?: string;
    fast41_candidate?: boolean;
    mw_hint?: number | null;
    federal_note?: string;
    conflict?: { active?: boolean; note?: string };
    portal?: string;
    disclaimer?: string;
  };
  community_friction?: {
    title?: string;
    headline?: string;
    score?: number;
    score_max?: number;
    band?: string;
    signals?: Array<{
      id?: string;
      label?: string;
      level?: number;
      detail?: string;
      verified?: boolean;
      source_url?: string | null;
    }>;
    verified?: boolean;
    disclaimer?: string;
  };
  recheck_diff?: {
    change_count?: number;
    changes?: string[];
  };
  regguard_stamp?: {
    grade?: string;
    label?: string;
    headline?: string;
    drivers?: Array<{
      severity?: string;
      label?: string;
      detail?: string;
      source_url?: string;
    }>;
    fingerprint?: string;
    stamped_at?: string;
    valid_until?: string;
    is_stale?: boolean;
    stale_reason?: string;
    disclaimer?: string;
  };
  stamp_grade?: string;
  stamp_label?: string;
  stamp_valid_until?: string;
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
  /** Paid product tiers for this email (partner / contractor_pro / ic_*) — hide buy CTAs already owned */
  entitlementTiers?: string[];
  /** IC purchased but PDFs not ready yet — show generate, not buy */
  icReportPending?: boolean;
  /**
   * Labeled sample ladder override — Free (blur), Estimator (partial), Pro (full desk).
   * When set, gating ignores share-unlock and paid entitlements.
   */
  demoTier?: 'free' | 'partner' | 'pro' | null;
}

/** Canonical shareable report link for social + clipboard + PDF/email CTAs. Never homepage. */
function reportShareUrl(analysis: AnalysisData, researchId?: string | null): string {
  const fromAnalysis = (analysis.share_url || '').trim();
  let raw = '';
  if (
    fromAnalysis &&
    fromAnalysis.includes('/r/') &&
    !fromAnalysis.endsWith('/r/') &&
    !fromAnalysis.endsWith('/r') &&
    !fromAnalysis.includes('utm_source=bid_receipt')
  ) {
    raw = fromAnalysis;
  } else {
    const rid = (researchId || analysis.research_id || '').trim();
    if (rid && !rid.startsWith('ephemeral-')) {
      raw = `https://app.regguardagent.com/r/${encodeURIComponent(rid)}`;
    }
  }
  if (!raw) return '';
  return withShareParams(raw, storedReferralCode() || (analysis as { referral_code?: string }).referral_code);
}

function hasUsableCoords(analysis: AnalysisData): boolean {
  const pi = analysis.project_info || ({} as AnalysisData['project_info']);
  const nested =
    (pi as { coordinates?: { latitude?: unknown; longitude?: unknown; lat?: unknown; lng?: unknown } })
      .coordinates || {};
  const pairs: Array<[unknown, unknown]> = [
    [(analysis as { latitude?: unknown }).latitude, (analysis as { longitude?: unknown }).longitude],
    [(analysis as { lat?: unknown }).lat, (analysis as { lng?: unknown }).lng],
    [(pi as { lat?: unknown }).lat, (pi as { lng?: unknown }).lng],
    [(pi as { latitude?: unknown }).latitude, (pi as { longitude?: unknown }).longitude],
    [nested.latitude, nested.longitude],
    [nested.lat, nested.lng],
  ];
  for (const [la, ln] of pairs) {
    const lat = Number(la);
    const lng = Number(ln);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
    if (Math.abs(lat) < 1e-6 && Math.abs(lng) < 1e-6) continue;
    if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) return true;
  }
  return false;
}

function isInstantPreviewDepth(analysis: AnalysisData): boolean {
  const src = String(analysis.honesty?.source || '').toLowerCase();
  if (src === 'instant' || src === 'preview' || src === 'delivery_summary') return true;
  if (analysis.preview && !hasUsableCoords(analysis)) return true;
  return false;
}

/** SMS/chat-forwardable receipt — bid-file memo, not a slogan. */
function formatShareDate(iso?: string): string {
  const raw = (iso || '').slice(0, 10);
  if (!raw) return '';
  const d = new Date(`${raw}T00:00:00`);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function stampCustomerDisplay(grade: string): string {
  const g = (grade || '').toUpperCase();
  if (g === 'FAIL' || g === 'HOLD') return 'HOLD';
  if (g === 'PASS' || g === 'CLEAR') return 'CLEAR';
  if (g === 'CAUTION') return 'CAUTION';
  return g;
}

function stampShareLabel(grade: string): string {
  const display = stampCustomerDisplay(grade);
  if (display === 'HOLD') return 'Hold';
  if (display === 'CLEAR') return 'Clear';
  if (display === 'CAUTION') return 'Caution';
  return grade;
}

function stampShareHeadline(grade: string, headline?: string): string {
  const display = stampCustomerDisplay(grade);
  const raw = (headline || '').replace(/\bFAIL\b/gi, 'HOLD').trim();
  if (raw) return raw;
  if (display === 'HOLD') return 'High pre-bid risk. Resolve the drivers below before treating the bid as clear.';
  if (display === 'CAUTION') return 'Material pre-bid risk — review drivers before locking a number.';
  if (display === 'CLEAR') return 'No Critical local killers on the current pack — still confirm with the AHJ before bid.';
  return '';
}

function stripMarkdownLite(text: string): string {
  return (text || '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '$1')
    .replace(/^#{1,6}\s+/, '')
    .replace(/^[-*]\s+(\[[ xX]\]\s*)?/, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Unique briefing from the action-plan memo. Checklist lines already live on the punch list. */
function extractScoutBriefing(md?: string | null): {
  watchdog: string;
  hits: string[];
  bottomLine: string;
  note: string;
} | null {
  const raw = (md || '').trim();
  if (!raw) return null;
  const chunks = raw.split(/\n(?=#{1,6}\s+)/);
  let watchdog = '';
  const hits: string[] = [];
  let bottomLine = '';
  const notes: string[] = [];

  for (const chunk of chunks) {
    const heading = (chunk.match(/^#{1,6}\s+(.+)/) || [])[1] || '';
    const body = chunk.replace(/^#{1,6}\s+.+/, '').trim();
    const head = heading.toUpperCase();
    const lines = body.split('\n').map((l) => l.trim()).filter(Boolean);
    const prose = lines
      .filter((l) => !/^[-*]\s+\[[ xX]?\]/.test(l) && !/^[-*]\s+/.test(l))
      .map(stripMarkdownLite)
      .filter((l) => l.length > 20);

    if (/FUTURE RISK|WATCHDOG|CODE-CHANGE/.test(head) || /Watchdog —/.test(body)) {
      watchdog = prose[0] || stripMarkdownLite(body).slice(0, 420);
      for (const l of lines) {
        const url = (l.match(/https?:\/\/\S+/) || [])[0];
        const label = stripMarkdownLite(l.replace(/https?:\/\/\S+/g, '')).slice(0, 90);
        if (url && !/^Mandatory/i.test(label)) hits.push(label ? `${label} — ${url}` : url);
      }
      continue;
    }
    if (/BOTTOM LINE/.test(head)) {
      bottomLine = prose.join(' ') || stripMarkdownLite(body);
      continue;
    }
    if (/PERMIT COST|TECHNICAL PUNCH|INSPECTION|REFERENCE LINK|CONTRACTOR ACTION/.test(head)) {
      continue;
    }
    if (prose.length && !lines.some((l) => /^[-*]\s+\[[ xX]?\]/.test(l))) {
      notes.push(...prose.slice(0, 2));
    }
  }

  if (!watchdog && /Watchdog — Code-change/i.test(raw)) {
    watchdog = stripMarkdownLite(
      (raw.match(/Watchdog[^\n]+(?:\n[^\n#][^\n]*)?/) || [''])[0]
    ).slice(0, 420);
  }
  if (!watchdog && !bottomLine && !notes.length) return null;
  return {
    watchdog,
    hits: hits.slice(0, 4),
    bottomLine,
    note: notes[0] || '',
  };
}

function cleanAhjName(name: string): string {
  return name.replace(/\s+AHJ\s*$/i, '').trim() || name;
}

function buildShareText(analysis: AnalysisData, generatedFor?: string, researchId?: string | null): string {
  const p = analysis.project_info;
  const ahj = cleanAhjName(analysis.ahj_card?.name || 'Local AHJ');
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

  const killerLines = killers
    .slice(0, 3)
    .map((k, i) => {
      const tier = String((k as { citation_tier?: string }).citation_tier || '').toLowerCase();
      const ver =
        tier === 'verified' || (k.verified && k.source_url)
          ? 'Source'
          : k.source_url
            ? 'linked source'
            : 'Unverified';
      const pri = (k.priority || 'Note').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
      const title = (k.title || 'Item').slice(0, 90);
      return `${i + 1}. ${title} — ${pri} · ${ver}`;
    })
    .join('\n');

  const who = (generatedFor || '').trim() || 'Estimator';
  const isDc = Boolean(
    analysis.dc_positioning ||
      analysis.planning_exposure_summary?.data_center_mode ||
      /data.?center|colo/i.test(p?.type || '')
  );
  const cov = resolveCoverage(analysis);
  const link = reportShareUrl(analysis, researchId);
  const stamp = analysis.regguard_stamp;
  const stampGrade = (stamp?.grade || analysis.stamp_grade || '').toUpperCase();
  const display = stampCustomerDisplay(stampGrade);
  const until = formatShareDate(stamp?.valid_until || analysis.stamp_valid_until);
  const headline = stampShareHeadline(stampGrade, stamp?.headline || stamp?.label);
  let stampBlock = '';
  if (display) {
    const validity = stamp?.is_stale
      ? 'STALE — re-run before bid submittal.'
      : until
        ? `Re-run before bid submittal (valid through ${until}).`
        : 'Re-run before bid submittal.';
    stampBlock = [`REGGUARD STAMP: ${display}`, headline, validity].filter(Boolean).join('\n');
  }

  const cityLine = [p?.city, p?.state, p?.zip].filter(Boolean).join(', ');
  const bandBlock =
    band?.pct_low != null && band?.pct_high != null
      ? [
          'SUGGESTED CONTINGENCY',
          `+${band.pct_low}% to +${band.pct_high}% (mid ${band.pct_mid}%)`,
          'Planning aid — not a bid quote.',
        ].join('\n')
      : 'Confirm contingency with the AHJ before bid.';

  return [
    'REG GUARD — BID RISK RECEIPT',
    '',
    p?.address || 'Site TBD',
    cityLine || null,
    '',
    `AHJ: ${ahj}`,
    `Coverage: ${cov.badge}`,
    '',
    stampBlock,
    '',
    bandBlock,
    killerLines ? `\nITEMS TO RESOLVE BEFORE BID\n${killerLines}` : null,
    isDc
      ? '\nMunicipal permits and utility interconnection often run on parallel clocks. This is not an interconnection study.'
      : null,
    '',
    `Prepared for ${who}`,
    'Confirm with the AHJ before bid or filing. Not a sealed bid or official filing.',
    link || 'Open your Reg Guard results to copy the receipt link.',
  ]
    .filter((line) => line != null)
    .join('\n')
    .replace(/\n{3,}/g, '\n\n');
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

/** Same box for CRITICAL / HIGH / MEDIUM / LOW — sized to the longest label, never stretched by the title. */
const PRIORITY_CHIP_LAYOUT =
  'inline-flex items-center justify-center self-start shrink-0 w-[5.5rem] h-6 rounded text-[10px] font-bold uppercase tracking-wide';

function PriorityChip({ priority }: { priority: string }) {
  return (
    <span className={`${PRIORITY_CHIP_LAYOUT} ${getPriorityBadge(priority)}`}>
      {priority}
    </span>
  );
}

const PRIORITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const;

function rankedPunchItems(view: AnalysisData): PunchListItemData[] {
  const raw = view.punch_list?.punch_list;
  const items = Array.isArray(raw) ? [...raw] : [];
  const rank = (p: string) => {
    const i = PRIORITY_ORDER.indexOf((p || '').toUpperCase() as (typeof PRIORITY_ORDER)[number]);
    return i === -1 ? 9 : i;
  };
  return items.sort((a, b) => rank(a.priority) - rank(b.priority));
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
  entitlementTiers = [],
  icReportPending = false,
  demoTier = null,
}: ResultsViewerModalProps) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState({
    environmental: true,
    punchList: true,
    critical: true,
    deepPlan: false,
  });
  const [copied, setCopied] = useState<'link' | 'text' | 'facebook' | 'instagram' | null>(null);
  const [sharePreviewOpen, setSharePreviewOpen] = useState(false);
  const [toast, setToast] = useState('');
  const [shareUnlocked, setShareUnlocked] = useState(() => {
    if (typeof window === 'undefined') return false;
    return sessionStorage.getItem('shareUnlocked') === '1';
  });
  const [packetLoading, setPacketLoading] = useState(false);
  const [recheckLoading, setRecheckLoading] = useState(false);
  const [liveAnalysis, setLiveAnalysis] = useState<AnalysisData | null>(null);
  const [gotchaText, setGotchaText] = useState('');
  const [gotchaBusy, setGotchaBusy] = useState(false);
  const [gotchaMsg, setGotchaMsg] = useState('');
  const [demandFeedbackSent, setDemandFeedbackSent] = useState(false);
  const [showDemandFeedback, setShowDemandFeedback] = useState(false);
  const [icOrderPdfs, setIcOrderPdfs] = useState<
    Array<{ type: string; name: string; url: string }>
  >([]);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const code = String((analysis as { referral_code?: string })?.referral_code || '').trim();
    if (code) rememberReferralCode(code);
  }, [analysis]);

  // Scroll the real app scroller (.platform-content), not window — otherwise the
  // executive summary can sit off-screen while the stamp looks like the top of results.
  useEffect(() => {
    if (!isOpen) return;
    const id = window.setTimeout(() => {
      const summary =
        document.getElementById('rg-executive-summary') ||
        document.getElementById('executive-summary');
      const scroller = document.querySelector('.platform-content') as HTMLElement | null;
      if (summary && scroller) {
        const top =
          summary.getBoundingClientRect().top -
          scroller.getBoundingClientRect().top +
          scroller.scrollTop -
          8;
        scroller.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
        return;
      }
      summary?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
    return () => window.clearTimeout(id);
  }, [isOpen, analysis]);

  useEffect(() => {
    setLiveAnalysis(null);
  }, [analysis]);

  // Load IC Project PDF download URLs only for IC-depth results (not free + stale session)
  useEffect(() => {
    if (!isOpen) return;
    const depthTierNow = String(analysis?.depth_tier || '').toLowerCase();
    const depthNow = String(analysis?.research_depth || '').toLowerCase();
    const ready =
      Boolean(analysis?.ic_pdfs_ready) ||
      depthTierNow === 'ic_full' ||
      depthNow === 'ic' ||
      depthNow === 'ic_full';
    if (!ready) {
      setIcOrderPdfs([]);
      return;
    }
    const email = (defaultEmail || '').trim().toLowerCase();
    if (!email) return;
    let cancelled = false;
    void fetch(backendUrl(`/orders?email=${encodeURIComponent(email)}`))
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (cancelled || !d) return;
        const orders = Array.isArray(d.orders) ? d.orders : [];
        const ic = orders.find(
          (o: { pdfs?: unknown[]; tier?: string; status?: string }) =>
            Array.isArray(o.pdfs) &&
            o.pdfs.length > 0 &&
            String(o.tier || '').toLowerCase().includes('ic')
        ) || orders.find((o: { pdfs?: unknown[] }) => Array.isArray(o.pdfs) && o.pdfs.length > 0);
        const pdfs = (ic?.pdfs || []) as Array<{ type?: string; name?: string; url?: string }>;
        const mapped = pdfs
          .filter((p) => p.url)
          .map((p) => ({
            type: String(p.type || 'report'),
            name: String(p.name || p.type || 'PDF'),
            url: String(p.url),
          }));
        // Prefer stable order: memo, punch, permits
        const order = ['research_memo', 'punch_list', 'permits'];
        mapped.sort((a, b) => order.indexOf(a.type) - order.indexOf(b.type));
        setIcOrderPdfs(mapped);
      })
      .catch(() => {
        if (!cancelled) setIcOrderPdfs([]);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, analysis?.ic_pdfs_ready, analysis?.depth_tier, analysis?.research_depth, defaultEmail]);

  useEffect(() => {
    if (!isOpen) return;
    const rid = researchId || analysis?.research_id;
    if (!rid) return;
    const email = (defaultEmail || '').trim();
    const q = email ? `?email=${encodeURIComponent(email)}` : '';
    void fetch(backendUrl(`/research/${encodeURIComponent(String(rid))}/share-unlock${q}`))
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.unlocked) {
          try {
            sessionStorage.setItem('shareUnlocked', '1');
          } catch {
            /* ignore */
          }
          setShareUnlocked(true);
        }
      })
      .catch(() => undefined);
  }, [isOpen, researchId, analysis?.research_id, defaultEmail]);

  if (!isOpen || !analysis) return null;

  const view = liveAnalysis || analysis;
  const coverage = resolveCoverage(view);

  /** City-pack body: prefer fee_card / gotcha_watchlist, fall back to local_pack rows */
  const packFees: Array<{
    trade?: string;
    label?: string;
    detail?: string;
    amount_usd?: number | null;
    amount_requires_schedule?: boolean;
    verified?: boolean;
    source_url?: string;
    source_label?: string;
    citation_url?: string;
    citation_note?: string;
    planning_aid?: boolean;
  }> = (() => {
    const fromCard = view.fee_card?.fees;
    if (Array.isArray(fromCard) && fromCard.length > 0) return fromCard;
    const fromLocal = view.local_pack?.fees;
    if (Array.isArray(fromLocal) && fromLocal.length > 0) {
      return fromLocal.map((row) => {
        const r = row as Record<string, unknown>;
        return {
          trade: typeof r.trade === 'string' ? r.trade : undefined,
          label: String(r.label || r.name || 'Fee line'),
          detail: typeof r.detail === 'string' ? r.detail : undefined,
          amount_usd: typeof r.amount_usd === 'number' ? r.amount_usd : null,
          amount_requires_schedule: Boolean(r.amount_requires_schedule),
          verified: Boolean(r.verified),
          source_url: typeof r.citation_url === 'string' ? r.citation_url : typeof r.source_url === 'string' ? r.source_url : undefined,
          source_label: typeof r.citation_note === 'string' ? r.citation_note : typeof r.source_label === 'string' ? r.source_label : undefined,
        };
      });
    }
    return [];
  })();

  const packGotchas: Array<{
    id?: string;
    title?: string;
    priority?: string;
    detail?: string;
    source_url?: string;
    source_label?: string;
  }> = (() => {
    const fromWl = view.gotcha_watchlist?.items;
    if (Array.isArray(fromWl) && fromWl.length > 0) return fromWl;
    const fromLocal = view.local_pack?.gotchas;
    if (Array.isArray(fromLocal) && fromLocal.length > 0) {
      return fromLocal.map((row, i) => {
        const r = row as Record<string, unknown>;
        const checklist = Array.isArray(r.checklist) ? r.checklist.map(String).slice(0, 2).join(' · ') : '';
        return {
          id: typeof r.id === 'string' ? r.id : `lp-g-${i}`,
          title: String(r.title || 'Local gotcha'),
          priority: String(r.priority || 'CAUTION'),
          detail: checklist || String(r.detail || r.citation_note || ''),
          source_url: typeof r.citation_url === 'string' ? r.citation_url : undefined,
          source_label: typeof r.citation_note === 'string' ? r.citation_note : undefined,
        };
      });
    }
    return [];
  })();

  const cityPackHasBody = Boolean(
    packFees.length ||
      packGotchas.length ||
      view.ahj_card ||
      view.contingency_band ||
      view.fee_card ||
      view.gotcha_watchlist ||
      view.inspection_sequence_card
  );

  const summary = buildSummaryFromAnalysis(view);
  const effectiveResearchId = researchId || view.research_id || null;
  const emailForCheckout = (defaultEmail || sessionStorage.getItem('userEmail') || '')
    .trim()
    .toLowerCase();
  const shareLink = reportShareUrl(view, effectiveResearchId);
  const shareText = buildShareText(view, emailForCheckout, effectiveResearchId);
  const shareTitle = `${stampShareLabel(view.regguard_stamp?.grade || view.stamp_grade || '')} — Bid Risk Receipt`.replace(
    /^ — /,
    ''
  );
  const depth = (view.research_depth || '').toLowerCase();
  const depthTier = (view.depth_tier || '').toLowerCase();
  const scoutMode = (view.scout_mode || '').toLowerCase();
  const incompleteRun =
    isInstantPreviewDepth(view) ||
    view.research_incomplete === true ||
    view.depth_claim_honest === false;
  // Never treat Instant Preview / missing pin as "deep Pro" for unlock chrome
  const isDeep =
    !incompleteRun &&
    (depth === 'pro' ||
      depth === 'pro_partial' ||
      depth === 'ic' ||
      depth === 'ic_full' ||
      depthTier === 'ic_full' ||
      depthTier === 'pro_local' ||
      depthTier === 'pro_light' ||
      depthTier === 'pro_partial');
  const isIcDepth =
    !incompleteRun &&
    (depthTier === 'ic_full' || depth === 'ic' || depth === 'ic_full');
  const offer = view.upgrade_offer;
  const proDelta = view.pro_delta;
  const buyerPersona = (view.buyer_persona || '').toLowerCase();
  const ladder = resolveResultsLadder({
    demoTier,
    entitlementTiers,
    accessTier: (view as { access_tier?: string }).access_tier || null,
    isDeep,
    isIcDepth,
    shareUnlocked,
  });
  const softLocked = ladder.softLocked;
  const punchVisible = ladder.punchVisible;
  const findingsVisible = ladder.findingsVisible;
  const ownsIc = ladder.ownsIc && isIcDepth && !incompleteRun;
  const canGenerateIcForSite = Boolean(icReportPending) && !ownsIc;
  const ownsPro = ladder.ownsPro;
  const ownsPartner = ladder.ownsPartner;
  const allowProDeskDownloads = ladder.allowProDesk;
  const blurProDesk = ladder.blurProDesk;
  const proBlurPunchTeasers = ladder.proBlurPunchTeasers;
  // Keep IC package download only for real IC-depth completed runs (demo never IC).
  const allowIcPackageDownload =
    demoTier === 'free' || demoTier === 'partner' || demoTier === 'pro'
      ? false
      : isIcDepth && !incompleteRun && ladder.ownsIc;
  const icPdfsReady =
    allowIcPackageDownload &&
    (Boolean(view.ic_pdfs_ready) ||
      (typeof window !== 'undefined' && sessionStorage.getItem('icPdfsReady') === '1'));

  const requireProDesk = (artifact: ProDeskArtifact): boolean => {
    if (allowProDeskDownloads) return true;
    showToast(proDeskGateMessage(artifact));
    return false;
  };

  const depthBadgeLabel = (() => {
    if (incompleteRun) {
      return (
        view.depth_badge ||
        'Free preview — not full Pro depth'
      );
    }
    const ultra =
      view.scout_locality_depth === 'local_ultralocal' ||
      Boolean(view.ultralocal_scout?.enabled);
    // Require real IC depth — do not promote free runs via leftover ic_package flags
    if (ultra && depthTier === 'ic_full') {
      return 'IC Project — full federal / state / local + ultralocal scout';
    }
    if (view.depth_badge && !/free|preview|instant/i.test(String(view.depth_badge))) {
      return view.depth_badge;
    }
    if (depthTier === 'ic_full') {
      return 'IC Project — full federal / state / local scout';
    }
    if (view.depth_badge) return view.depth_badge;
    if (depthTier === 'pro_light' || scoutMode === 'light')
      return 'Contractor Pro — local confirm + light scout';
    if (depthTier === 'pro_partial' || depth === 'pro_partial')
      return 'Contractor Pro — partial deep research';
    if (depthTier === 'pro_local' || (depth === 'pro' && scoutMode === 'none'))
      return 'Contractor Pro — paid local confirm';
    if (depth === 'pro') return 'Contractor Pro — deep research';
    return null;
  })();

  const checkoutTier = (
    tier?: string | null
  ): 'partner' | 'contractor_pro' | 'ic_project' | null => {
    const t = (tier || '').toLowerCase();
    if (t === 'partner' || t === 'contractor_pro' || t === 'ic_project') return t;
    if (t === 'ic_annual' || t === 'ic_consultant') return 'ic_project';
    return null;
  };

  const alreadyOwnsCheckout = (tier: 'partner' | 'contractor_pro' | 'ic_project'): boolean => {
    if (tier === 'partner') return ownsPartner && !incompleteRun;
    if (tier === 'contractor_pro') return ownsPro && !incompleteRun;
    // Never hide IC buy/upsell just because an old purchase is on file for another run
    if (tier === 'ic_project') return allowIcPackageDownload;
    return false;
  };

  /** F1: one primary upgrade block — hide CTAs for tiers already owned */
  const renderPrimaryUpgrade = () => {
    if (!offer?.message) return null;
    // IC-depth results: no further product upsell in the primary slot
    if (allowIcPackageDownload) return null;
    const primaryRaw = checkoutTier(offer.cta_tier);
    const secondaryRaw = checkoutTier(offer.secondary_cta_tier);
    const primary = primaryRaw && !alreadyOwnsCheckout(primaryRaw) ? primaryRaw : null;
    const secondary =
      secondaryRaw && !alreadyOwnsCheckout(secondaryRaw) && secondaryRaw !== primary
        ? secondaryRaw
        : null;
    // Unused IC credit for this site: show generate, not buy
    if (canGenerateIcForSite) {
      return (
        <section
          id="rg-primary-upgrade"
          className="rounded-xl border border-emerald-500/40 bg-gradient-to-br from-emerald-500/10 via-slate-900/70 to-slate-900/40 p-4 sm:p-5"
        >
          <div className="flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-emerald-300 shrink-0 mt-0.5" />
            <div className="min-w-0 flex-1">
              <h3 className="text-white font-bold text-sm sm:text-base">
                {IC_BUNDLE.generateHeadline}
              </h3>
              <p className="text-gray-300 text-sm mt-1.5 leading-relaxed">
                {IC_BUNDLE.generateBody}
              </p>
              {onUnlockDeeper ? (
                <button
                  type="button"
                  onClick={onUnlockDeeper}
                  disabled={unlockLoading}
                  className="mt-3 px-4 py-3 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm disabled:opacity-60"
                >
                  {unlockLoading ? 'Generating…' : 'Generate IC Report for this site'}
                </button>
              ) : (
                <a
                  href="/?run_ic=1"
                  className="mt-3 inline-flex px-4 py-3 min-h-[48px] items-center rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm"
                >
                  Generate IC Report for this site
                </a>
              )}
            </div>
          </div>
        </section>
      );
    }
    if (!primary && !secondary) return null;
    return (
      <section
        id="rg-primary-upgrade"
        className="rounded-xl border border-amber-500/35 bg-gradient-to-br from-amber-500/10 via-slate-900/70 to-blue-500/10 p-4 sm:p-5"
      >
        <div className="flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-amber-300 shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <h3 className="text-white font-bold text-sm sm:text-base">{offer.message}</h3>
            {offer.current_label && (
              <p className="text-xs text-gray-400 mt-1">
                Now: <span className="text-gray-200">{offer.current_label}</span>
                {offer.next_label ? (
                  <>
                    {' '}
                    → Next: <span className="text-emerald-300">{offer.next_label}</span>
                  </>
                ) : null}
              </p>
            )}
            {offer.detail && (
              <p className="text-gray-300 text-sm mt-1.5 leading-relaxed">{offer.detail}</p>
            )}
            {(offer.honesty_note || proDelta?.honesty) && (
              <p className="text-amber-200/90 text-xs mt-2 leading-relaxed">
                {offer.honesty_note || proDelta?.honesty}
              </p>
            )}
            <div className="flex flex-col sm:flex-row flex-wrap gap-2 mt-3">
              {primary && (
                <button
                  type="button"
                  onClick={() => goCheckout(primary)}
                  className="px-4 py-3 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm"
                >
                  {offer.cta_label || 'Continue'}
                </button>
              )}
              {secondary && offer.secondary_cta_label && (
                <button
                  type="button"
                  onClick={() => goCheckout(secondary)}
                  className="px-4 py-3 min-h-[48px] rounded-lg border border-slate-500 bg-slate-900/60 hover:bg-slate-800 text-white font-semibold text-sm"
                >
                  {offer.secondary_cta_label}
                </button>
              )}
            </div>
          </div>
        </div>
      </section>
    );
  };

  const renderLocalGotchas = () => {
    if (!view.gotcha_watchlist || !(view.gotcha_watchlist.items || []).length) return null;
    return (
      <section
        id="rg-local-gotchas"
        className="bg-slate-800/40 border border-amber-500/35 rounded-xl p-4 sm:p-5 space-y-3 scroll-mt-4"
      >
        <h3 className="text-amber-200 font-bold text-base">
          {view.gotcha_watchlist.title || 'Local gotcha watchlist'}
        </h3>
        <ul className="space-y-3">
          {(view.gotcha_watchlist.items || []).map((g) => (
            <li key={g.id || g.title} className="text-sm text-gray-300">
              <span className="text-amber-200 font-semibold">{g.priority}</span>{' '}
              <span className="text-white font-medium">{g.title}</span>
              <p className="text-gray-400 text-xs mt-0.5">{g.detail}</p>
              {(g.anti_patterns || []).length > 0 && (
                <p className="text-red-300/90 text-xs mt-1">
                  Don&apos;t: {(g.anti_patterns || []).join('; ')}
                </p>
              )}
              <CitationBadge
                verified={Boolean(g.source_url)}
                source_url={g.source_url}
                source_label={g.source_label || 'Unverified'}
              />
            </li>
          ))}
        </ul>
      </section>
    );
  };

  const formatStampSeverity = (raw?: string | null) => {
    const s = String(raw || '').toUpperCase();
    if (s === 'FAIL' || s === 'HOLD' || s === 'CRITICAL') return 'High Risk';
    if (s === 'CAUTION' || s === 'WARN' || s === 'WARNING' || s === 'HIGH') return 'Caution';
    if (s === 'PASS' || s === 'CLEAR' || s === 'OK') return 'Clear';
    return raw || 'Note';
  };

  /** Plain-text executive summary for download / SMS / copy */
  const buildExecutiveSummaryText = (): string => {
    const site =
      view.project_info?.address ||
      [view.project_info?.city, view.project_info?.state, view.project_info?.zip]
        .filter(Boolean)
        .join(', ') ||
      'This site';
    const ahjName =
      view.ahj_card?.name ||
      (view.project_info?.city ? `City of ${view.project_info.city}` : 'the local AHJ');
    const stampGrade = (view.regguard_stamp?.grade || view.stamp_grade || '').toUpperCase();
    const stampDisplay =
      stampGrade === 'FAIL' ? 'HOLD' : stampGrade === 'PASS' ? 'CLEAR' : stampGrade || '—';
    const band = view.contingency_band;
    const killers = (view.margin_killers || []).slice(0, 4);
    const share = reportShareUrl(view, effectiveResearchId);
    const lines = [
      'Reg Guard — Executive Summary',
      `Site: ${site}`,
      `AHJ: ${ahjName}`,
      `Stamp: ${stampDisplay}`,
      band
        ? `Suggested contingency: +${band.pct_low}% – +${band.pct_high}% (mid ${band.pct_mid}%)`
        : '',
      '',
      'Top items before bid:',
      ...killers.map(
        (k, i) => `${i + 1}. [${k.priority || 'NOTE'}] ${k.title || ''}${k.detail ? ` — ${k.detail}` : ''}`
      ),
      '',
      share ? `Full report / PDFs: ${share}` : '',
      'Planning aid only — confirm with AHJ before bid.',
    ].filter(Boolean);
    return lines.join('\n');
  };

  const forwardArtifact = async (artifactName: string, opts?: { downloadText?: boolean }) => {
    const site = view.project_info?.address || 'Site';
    const share = reportShareUrl(view, effectiveResearchId);
    const body = buildArtifactTextMessage({
      artifactName,
      site,
      shareUrl: share,
      extraLines:
        artifactName === 'Executive Summary'
          ? buildExecutiveSummaryText().split('\n').slice(3, 12)
          : [
              'Download the PDF from the share link (or from Results in Reg Guard).',
            ],
    });
    if (opts?.downloadText) {
      downloadTextFile(
        `RegGuard_${artifactName.replace(/\s+/g, '_')}.txt`,
        artifactName === 'Executive Summary' ? buildExecutiveSummaryText() : body
      );
      showToast(`${artifactName} downloaded`);
      return;
    }
    const ok = await copyText(body);
    textResultsToOthers(body);
    showToast(
      ok
        ? `${artifactName}: copied — Messages opened so you can text it`
        : `${artifactName}: Messages opened — paste if the body is empty`
    );
    trackStampEvent('artifact_forward', {
      researchId: effectiveResearchId,
      zip: view.project_info?.zip,
      stampGrade: view.regguard_stamp?.grade || view.stamp_grade,
      channel: 'sms_text',
      meta: { artifact: artifactName },
    });
  };

  /** Boardroom brief — never throw; always return visible markup */
  const renderExecutiveSummary = () => {
    try {
      const site =
        view.project_info?.address ||
        [view.project_info?.city, view.project_info?.state, view.project_info?.zip]
          .filter(Boolean)
          .join(', ') ||
        'This site';
      const ahjName =
        view.ahj_card?.name ||
        (view.project_info?.city ? `City of ${view.project_info.city}` : 'the local AHJ');
      const killers = Array.isArray(view.margin_killers) ? view.margin_killers.slice(0, 3) : [];
      const gotchas = Array.isArray(view.gotcha_watchlist?.items)
        ? view.gotcha_watchlist!.items!.slice(0, 3)
        : [];
      const punch = rankedPunchItems(view)
        .filter((p) => ['CRITICAL', 'HIGH'].includes((p.priority || '').toUpperCase()))
        .slice(0, 3);
      const envRisk = view.environmental_screening?.risk_level;
      const contingency = view.contingency_band;
      const stampGrade = (view.regguard_stamp?.grade || view.stamp_grade || '').toUpperCase();
      const stampDisplay =
        stampGrade === 'FAIL' ? 'HOLD' : stampGrade === 'PASS' ? 'CLEAR' : stampGrade || null;
      const stampDrivers = Array.isArray(view.regguard_stamp?.drivers)
        ? view.regguard_stamp!.drivers!.slice(0, 3)
        : [];

      const lead =
        stampDisplay === 'HOLD'
          ? `${site} presents elevated pre-bid risk under ${ahjName}. Municipal permitting and utility interconnection should be treated as parallel clocks until both paths are confirmed.`
          : stampDisplay === 'CAUTION'
            ? `${site} has material pre-bid items under ${ahjName} that warrant review before a bid number is locked.`
            : `${site}: the current local pack does not show Critical blockers. Confirm fees and portal requirements with ${ahjName} before bid.`;

      const priorityLines = [
        ...killers.map((k) => ({
          sev: formatStampSeverity(k.priority),
          title: String(k.title || 'Risk item'),
          detail: k.detail,
        })),
        ...gotchas.map((g) => ({
          sev: formatStampSeverity(g.priority),
          title: String(g.title || 'Gotcha'),
          detail: g.detail,
        })),
        ...stampDrivers.map((d) => ({
          sev: formatStampSeverity(d.severity),
          title: String(d.label || 'Driver'),
          detail: d.detail,
        })),
      ]
        .filter((item, idx, arr) => arr.findIndex((x) => x.title === item.title) === idx)
        .slice(0, 4);

      return (
        <section
          id="rg-executive-summary"
          data-rg-exec="1"
          style={{
            border: '3px solid #fbbf24',
            borderRadius: 12,
            padding: '20px 22px',
            background: 'linear-gradient(145deg,#1c1917 0%,#0c4a6e 55%,#020617 100%)',
            marginBottom: 12,
            boxShadow: '0 0 0 1px rgba(251,191,36,0.35), 0 12px 40px rgba(0,0,0,0.45)',
          }}
        >
          <p
            style={{
              fontSize: 12,
              fontWeight: 900,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              color: '#fde68a',
              margin: 0,
            }}
          >
            Executive summary
          </p>
          <h3
            style={{
              fontSize: 22,
              fontWeight: 900,
              color: '#fff',
              margin: '8px 0 0',
              lineHeight: 1.25,
            }}
          >
            {site}
          </h3>
          <p style={{ color: '#fff', fontSize: 15, lineHeight: 1.55, margin: '10px 0 0', maxWidth: 760 }}>
            {lead}
          </p>
          {stampDisplay ? (
            <p
              style={{
                display: 'inline-block',
                marginTop: 10,
                padding: '4px 10px',
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 800,
                color: '#fef3c7',
                border: '1px solid rgba(251,191,36,0.5)',
                background: 'rgba(251,191,36,0.12)',
              }}
            >
              RegGuard stamp: {stampDisplay}
            </p>
          ) : null}

          {contingency ? (
            <div
              style={{
                marginTop: 14,
                border: '1px solid rgba(251,191,36,0.4)',
                borderRadius: 10,
                padding: '12px 14px',
                background: 'rgba(251,191,36,0.1)',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <p
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: '#fde68a',
                  margin: 0,
                }}
              >
                Suggested bid contingency
              </p>
              <div style={{ filter: softLocked ? 'blur(7px)' : undefined, userSelect: softLocked ? 'none' : undefined }}>
                <p style={{ fontSize: 28, fontWeight: 800, color: '#fef3c7', margin: '4px 0 0' }}>
                  +{contingency.pct_low ?? '—'}% – +{contingency.pct_high ?? '—'}%
                </p>
                <p style={{ fontSize: 14, color: '#e2e8f0', margin: '8px 0 0', lineHeight: 1.5 }}>
                  Plan a {contingency.pct_low}%–{contingency.pct_high}% cushion on the base estimate for
                  local fees, review timing, and site risk
                  {contingency.pct_mid != null ? ` (midpoint ${contingency.pct_mid}%)` : ''}. Planning
                  aid only — confirm dollars with {ahjName}.
                </p>
              </div>
              {softLocked ? (
                <p style={{ fontSize: 12, color: '#fde68a', margin: '10px 0 0', fontWeight: 700 }}>
                  Free — contingency unlocks when you forward the Bid Risk Receipt or upgrade.
                </p>
              ) : blurProDesk ? (
                <p style={{ fontSize: 12, color: '#fcd34d', margin: '10px 0 0' }}>
                  Estimator — band shown. Full city pack / fee schedule stay on Contractor Pro.
                </p>
              ) : null}
            </div>
          ) : null}

          {priorityLines.length > 0 ? (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 14, fontWeight: 700, color: '#fff', margin: '0 0 8px' }}>
                What to resolve before bid
              </h4>
              <ol style={{ margin: 0, paddingLeft: 20 }}>
                {priorityLines.map((item, i) => {
                  const clearCount = softLocked ? 1 : blurProDesk ? 2 : priorityLines.length;
                  const locked = i >= clearCount;
                  return (
                    <li
                      key={`ex-p-${i}`}
                      style={{
                        color: '#e2e8f0',
                        fontSize: 14,
                        marginBottom: 8,
                        filter: locked ? 'blur(5px)' : undefined,
                        userSelect: locked ? 'none' : undefined,
                        position: 'relative',
                      }}
                    >
                      <span style={{ color: '#fde68a', fontWeight: 700, fontSize: 11, marginRight: 6 }}>
                        {item.sev}
                      </span>
                      <span style={{ color: '#fff', fontWeight: 600 }}>{item.title}</span>
                      {item.detail && (!softLocked || i === 0) ? (
                        <p
                          style={{
                            color: '#94a3b8',
                            fontSize: 12,
                            margin: '4px 0 0',
                            filter: softLocked || (blurProDesk && i >= 1) ? 'blur(4px)' : undefined,
                          }}
                        >
                          {item.detail}
                        </p>
                      ) : null}
                      {locked ? (
                        <span
                          style={{
                            position: 'absolute',
                            right: 0,
                            top: 0,
                            fontSize: 10,
                            fontWeight: 800,
                            letterSpacing: '0.06em',
                            textTransform: 'uppercase',
                            color: softLocked ? '#e9d5ff' : '#fde68a',
                            background: softLocked ? 'rgba(126,34,206,0.45)' : 'rgba(180,83,9,0.45)',
                            border: softLocked
                              ? '1px solid rgba(192,132,252,0.5)'
                              : '1px solid rgba(251,191,36,0.45)',
                            borderRadius: 4,
                            padding: '2px 6px',
                          }}
                        >
                          {softLocked ? 'Free locked' : 'Pro'}
                        </span>
                      ) : null}
                    </li>
                  );
                })}
              </ol>
            </div>
          ) : null}

          {punch.length > 0 ? (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 14, fontWeight: 700, color: '#fff', margin: '0 0 8px' }}>
                Immediate punch highlights
              </h4>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {punch.map((p, i) => {
                  const clearCount = softLocked ? 1 : blurProDesk ? 2 : punch.length;
                  const locked = i >= clearCount;
                  return (
                    <li
                      key={`ex-punch-${i}`}
                      style={{
                        color: '#e2e8f0',
                        fontSize: 14,
                        marginBottom: 6,
                        filter: locked ? 'blur(5px)' : undefined,
                        userSelect: locked ? 'none' : undefined,
                      }}
                    >
                      <span style={{ color: '#fca5a5', fontWeight: 700, fontSize: 11, marginRight: 6 }}>
                        {formatStampSeverity(p.priority)}
                      </span>
                      {p.task}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}

          {envRisk ? (
            <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 12 }}>
              Environmental screening risk: <span style={{ color: '#e2e8f0' }}>{envRisk}</span>
            </p>
          ) : null}

          <p
            style={{
              fontSize: 12,
              color: '#cbd5e1',
              borderTop: '1px solid rgba(251,191,36,0.25)',
              paddingTop: 12,
              marginTop: 14,
              lineHeight: 1.5,
            }}
          >
            {allowIcPackageDownload
              ? 'Your IC Diligence Bundle ZIP is ready below — decision memo, boardroom PDF, counsel DOCX, estimator Excel, and optional CSVs. This brief is the forwardable stamp.'
              : ownsIc
                ? 'Generate an IC Report for this site to unlock the Diligence Bundle ZIP download.'
                : isDeep
                  ? 'Upgrade to IC Project for the counsel-ready Diligence Bundle ZIP on this site.'
                  : 'This is a free preview brief. Estimator / Permit Runner and Contractor Pro unlock more depth; IC Project unlocks the Diligence Bundle ZIP.'}
          </p>
        </section>
      );
    } catch (err) {
      console.error('[RegGuard] executive summary render failed', err);
      return (
        <section
          id="rg-executive-summary"
          data-rg-exec="1"
          style={{
            border: '3px solid #fbbf24',
            borderRadius: 12,
            padding: 20,
            background: '#1c1917',
            color: '#fff',
          }}
        >
          <p style={{ fontWeight: 900, color: '#fde68a', margin: 0 }}>EXECUTIVE SUMMARY</p>
          <p style={{ marginTop: 8, lineHeight: 1.5 }}>
            {view.project_info?.address || 'This site'} — review contingency, stamp drivers, and punch
            list below before bid. (Summary renderer recovered from a data shape error.)
          </p>
        </section>
      );
    }
  };

  const jumpToCityPack = () => {
    setExpanded((prev) => ({ ...prev, punchList: true, critical: true }));
    const tryScroll = (attempt: number) => {
      const el =
        document.getElementById('rg-city-pack') ||
        document.getElementById('bid-arbitrage') ||
        document.getElementById('rg-local-gotchas');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        el.classList.add('ring-2', 'ring-emerald-400/70', 'ring-offset-2', 'ring-offset-slate-900');
        window.setTimeout(
          () => el.classList.remove('ring-2', 'ring-emerald-400/70', 'ring-offset-2', 'ring-offset-slate-900'),
          1800
        );
        showToast('Opened full city pack — fees & gotchas for this AHJ.');
        return;
      }
      if (attempt < 4) {
        window.setTimeout(() => tryScroll(attempt + 1), 80 * (attempt + 1));
        return;
      }
      showToast(
        coverage.tier === 'federal_state' || coverage.tier === 'portal_seed'
          ? 'No curated city pack for this ZIP yet — open the AHJ portal to confirm fees.'
          : 'City pack section is not on this results view — expand punch list or re-run with a pin.'
      );
    };
    window.requestAnimationFrame(() => tryScroll(0));
  };

  const renderProDelta = () => {
    if (!isDeep || !proDelta?.bullets?.length) return null;
    const isIc = depthTier === 'ic_full' || Boolean(view.ic_package);
    const title = isIc
      ? 'What IC-depth research added on this run'
      : 'What Contractor Pro added vs Free';
    const honesty =
      proDelta.honesty ||
      (isIc
        ? 'Research depth and citeable sources — not the Diligence Bundle contents, and not a guarantee fees match the live AHJ schedule.'
        : undefined);
    return (
      <section className="rounded-xl border border-emerald-500/35 bg-emerald-500/10 p-4 sm:p-5">
        <h3 className="text-emerald-200 font-bold text-sm sm:text-base">{title}</h3>
        {isIc && (
          <p className="text-xs text-emerald-100/80 mt-1 leading-relaxed">
            Scout / AHJ depth for this site — separate from the {IC_BUNDLE.productName} download
            below.
          </p>
        )}
        <ul className="mt-2 space-y-1.5">
          {proDelta.bullets.map((b) => (
            <li key={b} className="text-sm text-gray-200 flex gap-2">
              <span className="text-emerald-400 font-bold shrink-0">+</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
        {honesty && (
          <p className="text-xs text-amber-200/90 mt-3">{honesty}</p>
        )}
        {(buyerPersona === 'dc_infra' || buyerPersona === 'ic_shop') && depthTier !== 'ic_full' && (
          <p className="text-xs text-blue-200 mt-2">
            Data-center / infra tip: Pro light skips FAST-41 / water / moratorium passes — use IC for
            that depth + the Diligence Bundle.
          </p>
        )}
      </section>
    );
  };

  const downloadBidReceipt = async () => {
    setPacketLoading(true);
    try {
      const share = reportShareUrl(view, effectiveResearchId);
      const slim = analysisForPdfExport(view as unknown as Record<string, unknown>, effectiveResearchId);
      await postPdfDownload(
        backendUrl('/bid-receipt/pdf'),
        {
          analysis_data: slim,
          research_id: effectiveResearchId || undefined,
          generated_for: emailForCheckout || undefined,
          ...(share ? { share_url: share } : {}),
        },
        artifactDownloadFilename(view as unknown as Record<string, unknown>, 'BID RISK RECEIPT', 'pdf')
      );
      grantShareUnlock('bid_receipt_pdf');
      trackStampEvent('stamp_receipt_download', {
        researchId: effectiveResearchId,
        zip: view.project_info?.zip,
        stampGrade: view.regguard_stamp?.grade || view.stamp_grade,
        stampFingerprint: view.regguard_stamp?.fingerprint,
        channel: 'receipt_pdf',
      });
      showToast('Bid Risk Receipt downloaded');
      if (!demandFeedbackSent) setShowDemandFeedback(true);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Receipt download failed');
    } finally {
      setPacketLoading(false);
    }
  };

  const sendDemandFeedback = (answer: string) => {
    if (demandFeedbackSent) return;
    trackStampEvent('demand_feedback', {
      researchId: effectiveResearchId,
      zip: view.project_info?.zip,
      stampGrade: view.regguard_stamp?.grade || view.stamp_grade,
      stampFingerprint: view.regguard_stamp?.fingerprint,
      channel: 'post_receipt',
      meta: { answer },
    });
    setDemandFeedbackSent(true);
    setShowDemandFeedback(false);
    showToast('Thanks — that helps us measure what contractors need');
  };

  const downloadBidSheetCsv = async () => {
    if (!requireProDesk('bid_sheet_csv')) return;
    setPacketLoading(true);
    try {
      const res = await fetch(backendUrl('/research/bid-sheet.csv'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis: view }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Export failed (${res.status})`);
      }
      const blob = await res.blob();
      await downloadOnlyBlob(
        blob,
        artifactDownloadFilename(view as unknown as Record<string, unknown>, 'BID SHEET', 'csv')
      );
      showToast('Bid sheet CSV downloaded — paste into Excel (trade / owner / due_window / source_url hyperlinks).');
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'CSV export failed');
    } finally {
      setPacketLoading(false);
    }
  };

  const downloadBidSheetPdf = async () => {
    if (!requireProDesk('bid_sheet_pdf')) return;
    setPacketLoading(true);
    try {
      const res = await fetch(backendUrl('/research/bid-sheet.pdf'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis: view }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Bid sheet PDF failed (${res.status})`);
      }
      const blob = await res.blob();
      await downloadOnlyBlob(
        blob,
        artifactDownloadFilename(view as unknown as Record<string, unknown>, 'BID SHEET', 'pdf')
      );
      showToast('Bid sheet PDF downloaded — sources are clickable links.');
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Bid sheet PDF failed');
    } finally {
      setPacketLoading(false);
    }
  };

  const downloadCityPackPdf = async () => {
    if (!requireProDesk('city_pack_pdf')) return;
    setPacketLoading(true);
    try {
      const slim = analysisForPdfExport(view as unknown as Record<string, unknown>, effectiveResearchId);
      await postPdfDownload(
        backendUrl('/research/city-pack-pdf'),
        {
          analysis: slim,
          analysis_data: slim,
          research_id: effectiveResearchId || undefined,
        },
        artifactDownloadFilename(view as unknown as Record<string, unknown>, 'FULL CITY PACK', 'pdf')
      );
      showToast('Full city pack PDF downloaded — fees, gotchas, and AHJ links.');
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'City pack PDF failed');
    } finally {
      setPacketLoading(false);
    }
  };

  const downloadIcPdf = async (pdf: { type: string; name: string; url: string }) => {
    try {
      const raw = (pdf.url || '').trim();
      const pathStart = raw.search(/\/orders\//);
      let fetchUrl =
        pathStart >= 0 ? backendUrl(raw.slice(pathStart)) : raw.startsWith('http') ? raw : backendUrl(raw);
      const sep = fetchUrl.includes('?') ? '&' : '?';
      if (!/[?&]refresh=/.test(fetchUrl)) {
        fetchUrl = `${fetchUrl}${sep}refresh=1`;
      }
      const res = await fetch(fetchUrl, { credentials: 'omit' });
      if (!res.ok) throw new Error(`Download failed (${res.status})`);
      const blob = await res.blob();
      await downloadOnlyBlob(
        blob,
        pdf.type === 'ic_package'
          ? artifactDownloadFilename(view as unknown as Record<string, unknown>, 'IC DILIGENCE PACKAGE', 'pdf')
          : `${(pdf.type || 'report').replace(/[^\w.-]+/g, '_')}.pdf`
      );
      showToast(`${pdf.name} downloaded`);
    } catch {
      showToast('Could not download PDF — try My Orders or refresh.');
    }
  };

  const downloadIcDiligenceBundle = async () => {
    if (!allowIcPackageDownload) {
      showToast(
        'IC Diligence Bundle requires an IC Project run for this site — free preview cannot download it.'
      );
      return;
    }
    setPacketLoading(true);
    try {
      const slim = analysisForPdfExport(view as unknown as Record<string, unknown>, effectiveResearchId);
      await postBinaryDownload(
        backendUrl('/ic-package/bundle'),
        {
          analysis_data: slim,
          research_id: effectiveResearchId || undefined,
          generated_for: emailForCheckout || undefined,
          email: emailForCheckout || undefined,
        },
        artifactDownloadFilename(view as unknown as Record<string, unknown>, 'IC DILIGENCE BUNDLE', 'zip'),
        ['application/zip', 'application/octet-stream']
      );
      trackStampEvent('ic_bundle_download', {
        researchId: effectiveResearchId,
        zip: view.project_info?.zip,
        stampGrade: view.regguard_stamp?.grade || view.stamp_grade,
        channel: 'results',
        meta: {
          artifact: 'ic_diligence_bundle_zip',
          depth_tier: view.depth_tier || view.research_depth || '',
        },
      });
      showToast(
        'IC Diligence Bundle downloaded — decision memo + boardroom PDF + counsel DOCX + Excel + optional CSVs'
      );
    } catch (e) {
      trackStampEvent('ic_bundle_download_fail', {
        researchId: effectiveResearchId,
        zip: view.project_info?.zip,
        channel: 'results',
        meta: { error: e instanceof Error ? e.message : 'fail' },
      });
      showToast(e instanceof Error ? e.message : 'IC Diligence Bundle download failed');
    } finally {
      setPacketLoading(false);
    }
  };

  const downloadIcBoardroomPackage = async () => {
    if (!allowIcPackageDownload) {
      showToast(
        'IC Diligence Package requires an IC Project run for this site — free preview cannot download it.'
      );
      return;
    }
    setPacketLoading(true);
    try {
      const slim = analysisForPdfExport(view as unknown as Record<string, unknown>, effectiveResearchId);
      await postPdfDownload(
        backendUrl('/ic-package/pdf'),
        {
          analysis_data: slim,
          research_id: effectiveResearchId || undefined,
          generated_for: emailForCheckout || undefined,
          email: emailForCheckout || undefined,
        },
        artifactDownloadFilename(view as unknown as Record<string, unknown>, 'IC DILIGENCE PACKAGE', 'pdf')
      );
      trackStampEvent('ic_artifact_download', {
        researchId: effectiveResearchId,
        zip: view.project_info?.zip,
        stampGrade: view.regguard_stamp?.grade || view.stamp_grade,
        channel: 'results',
        meta: { artifact: 'boardroom_pdf' },
      });
      showToast('IC Diligence Package PDF downloaded — full boardroom brief for IC / interconnection review');
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'IC package download failed');
    } finally {
      setPacketLoading(false);
    }
  };

  const downloadIcEvidenceCsv = async () => {
    if (!allowIcPackageDownload) {
      showToast(
        'Evidence index requires an IC Project run for this site — free preview cannot download it.'
      );
      return;
    }
    setPacketLoading(true);
    try {
      const slim = analysisForPdfExport(view as unknown as Record<string, unknown>, effectiveResearchId);
      await postBinaryDownload(
        backendUrl('/ic-package/evidence-csv'),
        {
          analysis_data: slim,
          research_id: effectiveResearchId || undefined,
          generated_for: emailForCheckout || undefined,
          email: emailForCheckout || undefined,
        },
        artifactDownloadFilename(view as unknown as Record<string, unknown>, 'EVIDENCE INDEX', 'csv'),
        ['text/csv', 'application/octet-stream']
      );
      trackStampEvent('ic_artifact_download', {
        researchId: effectiveResearchId,
        zip: view.project_info?.zip,
        channel: 'results',
        meta: { artifact: 'evidence_index_csv' },
      });
      showToast('Evidence index CSV downloaded — claim → exhibit → source_url');
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Evidence index download failed');
    } finally {
      setPacketLoading(false);
    }
  };

  const downloadIcFeePunchCsv = async () => {
    if (!allowIcPackageDownload) {
      showToast(
        'Fee / punch CSV requires an IC Project run for this site — free preview cannot download it.'
      );
      return;
    }
    setPacketLoading(true);
    try {
      const res = await fetch(backendUrl('/research/bid-sheet.csv'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis: view }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Export failed (${res.status})`);
      }
      const blob = await res.blob();
      await downloadOnlyBlob(
        blob,
        artifactDownloadFilename(
          view as unknown as Record<string, unknown>,
          'FEE PUNCH SCHEDULE',
          'csv'
        )
      );
      trackStampEvent('ic_artifact_download', {
        researchId: effectiveResearchId,
        zip: view.project_info?.zip,
        channel: 'results',
        meta: { artifact: 'fee_punch_csv' },
      });
      showToast('Fee / punch CSV downloaded — trade / owner / due_window / exhibit_id / source_url');
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'CSV export failed');
    } finally {
      setPacketLoading(false);
    }
  };

  const downloadIcBoardroomDocx = async () => {
    if (!allowIcPackageDownload) {
      showToast(
        'IC Diligence DOCX requires an IC Project run for this site — free preview cannot download it.'
      );
      return;
    }
    setPacketLoading(true);
    try {
      const slim = analysisForPdfExport(view as unknown as Record<string, unknown>, effectiveResearchId);
      await postBinaryDownload(
        backendUrl('/ic-package/docx'),
        {
          analysis_data: slim,
          research_id: effectiveResearchId || undefined,
          generated_for: emailForCheckout || undefined,
          email: emailForCheckout || undefined,
        },
        artifactDownloadFilename(view as unknown as Record<string, unknown>, 'IC DILIGENCE PACKAGE', 'docx'),
        [
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'application/octet-stream',
        ]
      );
      trackStampEvent('ic_artifact_download', {
        researchId: effectiveResearchId,
        zip: view.project_info?.zip,
        channel: 'results',
        meta: { artifact: 'boardroom_docx' },
      });
      showToast('IC Diligence DOCX downloaded — editable for counsel redlines; sources are hyperlinks');
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'IC DOCX download failed');
    } finally {
      setPacketLoading(false);
    }
  };

  const downloadBidPacketFull = async () => {
    if (!requireProDesk('bid_packet_pdf')) return;
    setPacketLoading(true);
    try {
      const res = await fetch(backendUrl('/bid-packet/pdf'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis_data: view, mode: 'full' }),
      });
      const ctype = (res.headers.get('content-type') || '').toLowerCase();
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail =
          typeof data.detail === 'string'
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((d: { msg?: string }) => d.msg || String(d)).join('; ')
              : 'Bid packet failed';
        throw new Error(detail);
      }
      let blob: Blob;
      if (ctype.includes('application/pdf')) {
        blob = await res.blob();
      } else {
        const data = await res.json().catch(() => ({}));
        const rawUrl = String(data.download_url || '');
        if (!rawUrl) throw new Error('Bid packet generated but no PDF returned');
        const pathStart = rawUrl.search(/\/bid-packet\//);
        const fetchUrl =
          pathStart >= 0
            ? backendUrl(rawUrl.slice(pathStart))
            : rawUrl.startsWith('http')
              ? rawUrl
              : backendUrl(rawUrl);
        const fileRes = await fetch(fetchUrl, { credentials: 'omit' });
        if (!fileRes.ok) throw new Error(`Bid packet download failed (${fileRes.status})`);
        blob = await fileRes.blob();
      }
      await downloadOnlyBlob(blob, 'RegGuard_Bid_Packet.pdf');
      showToast('Full bid packet PDF downloaded — citeable pre-bid diligence, not a sealed bid');
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Bid packet failed');
    } finally {
      setPacketLoading(false);
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

  const freezeWarRoomStamp = async () => {
    const rid = (effectiveResearchId || '').trim();
    if (!rid) {
      setToast('Report not found — cannot freeze stamp.');
      window.setTimeout(() => setToast(''), 3500);
      return;
    }
    try {
      const res = await fetch(
        backendUrl(`/research/${encodeURIComponent(rid)}/war-room/freeze`),
        { method: 'POST' }
      );
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error((detail as { detail?: string }).detail || `Freeze failed (${res.status})`);
      }
      setToast('Stamp locked — grade and fingerprint frozen for dispute records.');
      window.setTimeout(() => setToast(''), 3500);
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Could not lock stamp');
    }
  };

  const goCheckout = (tier: 'partner' | 'contractor_pro' | 'ic_project') => {
    // Persist site so return after payment can deepen the same lookup
    try {
      const pi = view.project_info;
      persistLastResearchForm({
        address: pi.address || '',
        city: pi.city || '',
        state: pi.state || '',
        zip: pi.zip || '',
        projectType: pi.type || 'commercial',
        email: emailForCheckout,
      });
      if (emailForCheckout) sessionStorage.setItem('userEmail', emailForCheckout);
      sessionStorage.setItem('pendingDeepUnlock', '1');
      if (tier === 'ic_project') {
        setPendingIcReport(true);
      } else {
        setPendingIcReport(false);
      }
    } catch {
      /* ignore */
    }
    const q = emailForCheckout ? `?email=${encodeURIComponent(emailForCheckout)}` : '';
    navigate(`/checkout/${tier}${q}`);
  };

  const grantShareUnlock = (channel: string = 'share') => {
    try {
      sessionStorage.setItem('shareUnlocked', '1');
    } catch {
      /* ignore */
    }
    setShareUnlocked(true);
    setToast('Full free punch list unlocked — forward the Bid Risk Receipt next.');
    window.setTimeout(() => setToast(''), 4000);
    const rid = effectiveResearchId;
    if (rid) {
      const referralCode =
        (typeof window !== 'undefined' &&
          (sessionStorage.getItem('referralCode') ||
            localStorage.getItem('referralCode') ||
            sessionStorage.getItem('affiliateCode'))) ||
        '';
      void fetch(backendUrl(`/research/${encodeURIComponent(rid)}/share-unlock`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: (defaultEmail || '').trim(),
          channel,
          referral_code: referralCode || undefined,
        }),
      })
        .then(async (res) => {
          const data = await res.json().catch(() => ({}));
          const fwd = data?.rewards?.forwarder_credit;
          const part = data?.rewards?.partner_credit;
          if (fwd || part) {
            const bits = [];
            if (fwd) bits.push(`$${fwd.delta_usd ?? 5} forward credit`);
            if (part) bits.push(`$${part.delta_usd ?? 10} partner credit`);
            setToast(`Receipt forwarded — ${bits.join(' · ')} applied.`);
            window.setTimeout(() => setToast(''), 4500);
          }
        })
        .catch(() => undefined);
    }
  };

  const toggle = (key: keyof typeof expanded) => {
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(''), 3200);
  };

  const copyToClipboard = async (text: string): Promise<boolean> => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch {
      /* fall through */
    }
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  };

  const copyShareText = async (kind: 'text' | 'facebook' | 'instagram' = 'text') => {
    const ok = await copyToClipboard(shareText);
    if (ok) {
      setCopied(kind);
      window.setTimeout(() => setCopied(null), 2000);
      grantShareUnlock();
      trackStampEvent(
        kind === 'facebook' ? 'stamp_share_facebook' : 'stamp_share_copy',
        {
          researchId: effectiveResearchId,
          zip: view.project_info?.zip,
          stampGrade: view.regguard_stamp?.grade || view.stamp_grade,
          stampFingerprint: view.regguard_stamp?.fingerprint,
          channel: kind,
        }
      );
      if (kind === 'instagram') {
        showToast('Caption copied — paste in Instagram DM, Story, or post');
      } else if (kind === 'facebook') {
        showToast('Summary copied — paste into your Facebook post');
      } else {
        showToast('Receipt copied');
      }
      return true;
    }
    setSharePreviewOpen(true);
    showToast('Select the text below and copy manually');
    return false;
  };

  const openWhatsApp = () => {
    // Keep URL under common mobile limits
    const text = shareText.length > 1400 ? `${shareText.slice(0, 1350)}\n…\nReport: ${shareLink}` : shareText;
    window.open(
      `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`,
      '_blank',
      'noopener,noreferrer'
    );
    grantShareUnlock();
    trackStampEvent('stamp_share_whatsapp', {
      researchId: effectiveResearchId,
      zip: view.project_info?.zip,
      stampGrade: view.regguard_stamp?.grade || view.stamp_grade,
      stampFingerprint: view.regguard_stamp?.fingerprint,
      channel: 'whatsapp',
    });
    showToast('WhatsApp opened with your Bid Risk Receipt');
  };

  const openFacebook = async () => {
    await copyShareText('facebook');
    const u = encodeURIComponent(shareLink);
    const quote = encodeURIComponent(shareText.slice(0, 500));
    window.open(
      `https://www.facebook.com/sharer/sharer.php?u=${u}&quote=${quote}`,
      '_blank',
      'noopener,noreferrer'
    );
  };

  const openInstagram = async () => {
    await copyShareText('instagram');
    setSharePreviewOpen(true);
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
        <div className="flex flex-col gap-4 px-5 sm:px-8 py-5 border-b border-slate-700/80 bg-slate-900/90">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 id="results-modal-title" className="text-2xl sm:text-3xl font-black text-white">
                Site Diligence Results
              </h2>
              <p className="text-gray-400 text-sm mt-1">
                {(() => {
                  const pi = view.project_info || ({} as AnalysisData['project_info']);
                  const street = (pi.address || '').trim();
                  const place = `${pi.city || ''}, ${pi.state || ''} ${pi.zip || ''}`.trim();
                  const sn = street.toLowerCase().replace(/[^a-z0-9]/g, '');
                  const cn = (pi.city || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                  if (cn && sn.includes(cn) && street.includes(String(pi.zip || ''))) {
                    return street || place || 'Site address';
                  }
                  return [street, place].filter(Boolean).join(' · ') || 'Site address';
                })()}
              </p>
              {(depthBadgeLabel || view.research_depth === 'pro' || view.research_depth === 'pro_partial') && (
                <p
                  className={`mt-2 inline-flex items-center px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide border ${
                    isInstantPreviewDepth(view)
                      ? 'bg-amber-500/20 text-amber-200 border-amber-500/40'
                      : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                  }`}
                >
                  {depthBadgeLabel ||
                    (view.research_depth === 'pro'
                      ? 'Contractor Pro — deep research'
                      : 'Contractor Pro — partial deep research')}
                </p>
              )}
              {view.depth_claim_note && (
                <p className="mt-1.5 text-xs text-amber-200/90 max-w-2xl">{view.depth_claim_note}</p>
              )}
              {!isDeep && !depthBadgeLabel && (
                <p className="mt-2 inline-flex items-center px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide bg-amber-500/15 text-amber-200 border border-amber-500/35">
                  Free preview — citeable fees & top punch lines
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-slate-800 transition shrink-0"
              aria-label="Close results"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
            <button
              type="button"
              onClick={() => void forwardArtifact('Bid Risk Receipt')}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg border border-emerald-400/50 bg-emerald-500/15 text-emerald-100 text-sm font-bold"
            >
              <Share2 className="w-4 h-4 shrink-0" />
              Forward
            </button>
            <button
              type="button"
              onClick={() => void downloadBidReceipt()}
              disabled={packetLoading}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-black disabled:opacity-50"
            >
              <Download className="w-4 h-4 shrink-0" />
              {packetLoading ? 'Opening…' : 'Download'}
            </button>
          </div>
        </div>

        {demoTier ? (
          <div className="px-5 sm:px-8 py-3 border-b border-emerald-500/30 bg-emerald-500/10">
            <p className="text-sm font-bold text-emerald-100">
              {demoTier === 'free'
                ? 'SAMPLE Free Lookups — fewest lines · locked sections blurred'
                : demoTier === 'partner'
                  ? 'SAMPLE Estimator / Permit Runner — more unlocked · Pro desk still locked'
                  : 'SAMPLE Contractor Pro — full Pro desk unlocked'}
            </p>
          </div>
        ) : null}
        {/* Stay-oriented: jump without losing this results session */}
        <div className="px-5 sm:px-8 py-2 border-b border-slate-700/60 bg-slate-950/80 flex flex-wrap gap-2 text-xs sm:text-sm">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-2 min-h-[40px] rounded-lg border border-slate-600 text-gray-200 hover:bg-slate-800 font-semibold"
          >
            ← Back to form (results stay saved)
          </button>
          <button
            type="button"
            onClick={() => {
              const summary = document.getElementById('rg-executive-summary');
              const scroller = document.querySelector('.platform-content') as HTMLElement | null;
              if (summary && scroller) {
                const top =
                  summary.getBoundingClientRect().top -
                  scroller.getBoundingClientRect().top +
                  scroller.scrollTop -
                  8;
                scroller.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
                return;
              }
              summary?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }}
            className="px-3 py-2 min-h-[40px] rounded-lg border border-sky-500/50 bg-sky-500/15 text-sky-100 hover:bg-sky-500/25 font-bold"
          >
            Executive summary
          </button>
          <a
            href="/orders?from=results"
            className="px-3 py-2 min-h-[40px] inline-flex items-center rounded-lg border border-slate-600 text-gray-200 hover:bg-slate-800 font-semibold"
          >
            My Orders
          </a>
          <a
            href="/jobs"
            className="px-3 py-2 min-h-[40px] inline-flex items-center rounded-lg border border-slate-600 text-gray-200 hover:bg-slate-800 font-semibold"
          >
            My Jobs
          </a>
          {reportShareUrl(view, effectiveResearchId) ? (
            <a
              href={reportShareUrl(view, effectiveResearchId) || '#'}
              className="px-3 py-2 min-h-[40px] inline-flex items-center rounded-lg border border-emerald-500/40 text-emerald-200 hover:bg-emerald-500/10 font-semibold"
            >
              Share link (/r/…)
            </a>
          ) : null}
        </div>

        {incompleteRun && (
          <div className="mx-5 sm:mx-8 mt-4 rounded-xl border border-amber-500/45 bg-amber-500/10 px-4 py-3">
            <p className="text-sm font-bold text-amber-100">Run finished — deep site research incomplete</p>
            <p className="text-xs text-amber-200/90 mt-1 leading-relaxed">
              {view.depth_claim_note ||
                'Confirm the map pin (lat/lng) and re-check before forwarding as Contractor Pro / IC diligence. Environmental cards marked PRELIMINARY mean GIS did not run for this parcel.'}
            </p>
            {onUnlockDeeper && (
              <button
                type="button"
                onClick={() => onUnlockDeeper()}
                className="mt-3 px-3 py-2 min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold"
              >
                Confirm pin &amp; re-run deep research
              </button>
            )}
          </div>
        )}

        {/* Executive summary + IC PDFs — summary is INSIDE the green card users stare at */}
        <div className="px-5 sm:px-8 py-4 border-b border-emerald-500/30 bg-slate-950/90 space-y-4">
          <div
            id="ic-project-report-pdfs"
            className={`rounded-xl border p-4 space-y-4 ${
              allowIcPackageDownload
                ? 'border-emerald-500/40 bg-emerald-500/10'
                : 'border-slate-600/50 bg-slate-900/50'
            }`}
          >
            <div id="executive-summary" className="scroll-mt-4">
              {renderExecutiveSummary()}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void forwardArtifact('Executive Summary')}
                  className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold"
                >
                  <Share2 className="w-4 h-4" />
                  Forward summary
                </button>
                <button
                  type="button"
                  onClick={() => void forwardArtifact('Executive Summary', { downloadText: true })}
                  className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg bg-amber-500/20 border border-amber-400/50 text-amber-100 text-sm font-semibold hover:bg-amber-500/30"
                >
                  <Download className="w-4 h-4" />
                  Download summary
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    const ok = await copyText(buildExecutiveSummaryText());
                    showToast(ok ? 'Executive summary copied' : 'Could not copy — try Download');
                  }}
                  className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg border border-white/20 bg-white/5 text-gray-200 text-sm font-semibold"
                >
                  <Copy className="w-4 h-4" />
                  Copy summary
                </button>
              </div>
            </div>

            {renderProDelta()}

            {allowIcPackageDownload ? (
              <>
                <div>
                  <p className="text-emerald-200 font-bold text-sm sm:text-base">
                    {IC_BUNDLE.readyHeadline}
                  </p>
                  <p className="text-gray-300 text-sm mt-1 leading-relaxed">{IC_BUNDLE.readyBody}</p>
                </div>
                <IcDiligenceBundlePitch variant="inline" className="rounded-xl border border-emerald-500/25 bg-slate-950/40 p-3.5" />
                <button
                  type="button"
                  disabled={packetLoading}
                  onClick={() => void downloadIcDiligenceBundle()}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-3.5 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-base font-black disabled:opacity-50"
                >
                  <Download className="w-5 h-5 shrink-0" />
                  {packetLoading ? 'Building bundle…' : IC_BUNDLE.ctaDownload}
                </button>
                <div className="grid sm:grid-cols-2 gap-2">
                  <button
                    type="button"
                    disabled={packetLoading}
                    onClick={() => void downloadIcBoardroomPackage()}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2.5 min-h-[44px] rounded-lg border border-emerald-400/50 bg-emerald-500/10 text-emerald-100 text-sm font-bold disabled:opacity-50"
                  >
                    <Download className="w-4 h-4 shrink-0" />
                    Boardroom PDF
                  </button>
                  <button
                    type="button"
                    disabled={packetLoading}
                    onClick={() => void downloadBidReceipt()}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2.5 min-h-[44px] rounded-lg border border-emerald-400/50 bg-emerald-500/10 text-emerald-100 text-sm font-bold disabled:opacity-50"
                  >
                    <Download className="w-4 h-4 shrink-0" />
                    Decision memo PDF
                  </button>
                  <button
                    type="button"
                    disabled={packetLoading}
                    onClick={() => void downloadIcBoardroomDocx()}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2.5 min-h-[44px] rounded-lg border border-sky-400/50 bg-sky-500/10 text-sky-100 text-sm font-bold disabled:opacity-50"
                  >
                    <Download className="w-4 h-4 shrink-0" />
                    Counsel DOCX
                  </button>
                  <button
                    type="button"
                    disabled={packetLoading}
                    onClick={() => void downloadIcFeePunchCsv()}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2.5 min-h-[44px] rounded-lg border border-sky-400/50 bg-sky-500/10 text-sky-100 text-sm font-bold disabled:opacity-50"
                  >
                    <Download className="w-4 h-4 shrink-0" />
                    Fee / punch CSV
                  </button>
                  <button
                    type="button"
                    disabled={packetLoading}
                    onClick={() => void downloadIcEvidenceCsv()}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2.5 min-h-[44px] rounded-lg border border-sky-400/50 bg-sky-500/10 text-sky-100 text-sm font-bold disabled:opacity-50 sm:col-span-2"
                  >
                    <Download className="w-4 h-4 shrink-0" />
                    Evidence index CSV
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => void forwardArtifact('IC Diligence Bundle')}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 min-h-[48px] rounded-lg border border-emerald-400/50 bg-emerald-500/10 text-emerald-100 text-sm font-bold"
                >
                  <MessageSquare className="w-4 h-4 shrink-0" />
                  Text IC Diligence Bundle link
                </button>
                {icPdfsReady ? (
                  (() => {
                    const parts = icOrderPdfs.filter((p) => p.type !== 'ic_package');
                    const primary = icOrderPdfs.find((p) => p.type === 'ic_package');
                    return (
                      <>
                        {primary ? (
                          <button
                            type="button"
                            onClick={() => void downloadIcPdf(primary)}
                            className="w-full inline-flex items-center justify-center gap-2 px-3 py-2.5 min-h-[44px] rounded-lg border border-emerald-400/40 bg-emerald-500/10 text-emerald-100 text-sm font-bold"
                          >
                            <Download className="w-4 h-4 shrink-0" />
                            Re-download from My Orders
                          </button>
                        ) : null}
                        {parts.length > 0 ? (
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
                              Other order PDFs
                            </p>
                            <div className="grid sm:grid-cols-3 gap-2">
                              {parts.map((pdf) => (
                                <button
                                  key={pdf.type}
                                  type="button"
                                  onClick={() => void downloadIcPdf(pdf)}
                                  className="inline-flex items-center justify-center gap-2 px-3 py-2.5 min-h-[44px] rounded-lg border border-emerald-500/35 bg-slate-950/40 hover:bg-slate-900 text-emerald-100 text-sm font-semibold"
                                >
                                  <Download className="w-4 h-4 shrink-0" />
                                  <span className="truncate">{pdf.name}</span>
                                </button>
                              ))}
                            </div>
                          </div>
                        ) : icOrderPdfs.length === 0 ? (
                          <p className="text-xs text-amber-100/90">
                            Loading order links… you can still download the Diligence Bundle above.
                          </p>
                        ) : null}
                      </>
                    );
                  })()
                ) : (
                  <p className="text-xs text-gray-400">
                    Bundle builds on demand from this IC results set. For order history, open My
                    Orders.
                  </p>
                )}
              </>
            ) : canGenerateIcForSite ? (
              <div className="space-y-3">
                <p className="text-amber-100 font-bold text-sm sm:text-base">
                  {IC_BUNDLE.generateHeadline}
                </p>
                <p className="text-gray-300 text-sm leading-relaxed">{IC_BUNDLE.generateBody}</p>
                <IcDiligenceBundlePitch variant="compact" />
                {onUnlockDeeper ? (
                  <button
                    type="button"
                    onClick={onUnlockDeeper}
                    disabled={unlockLoading}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-3.5 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-base font-bold disabled:opacity-50"
                  >
                    {unlockLoading ? 'Generating…' : IC_BUNDLE.ctaGenerate}
                  </button>
                ) : (
                  <a
                    href="/?run_ic=1"
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-3.5 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-base font-bold"
                  >
                    {IC_BUNDLE.ctaGenerate}
                  </a>
                )}
              </div>
            ) : isDeep ? (
              <div className="space-y-3">
                <p className="text-slate-200 font-bold text-sm sm:text-base">
                  {IC_BUNDLE.upsellHeadline}
                </p>
                <p className="text-gray-300 text-sm leading-relaxed">{IC_BUNDLE.upsellBody}</p>
                <IcDiligenceBundlePitch variant="compact" />
                {!alreadyOwnsCheckout('ic_project') && (
                  <button
                    type="button"
                    onClick={() => goCheckout('ic_project')}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-3.5 min-h-[48px] rounded-lg border border-emerald-500/50 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-100 text-base font-bold"
                  >
                    {IC_BUNDLE.ctaUnlock}
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-slate-200 font-bold text-sm sm:text-base">
                  {IC_BUNDLE.lockedHeadline}
                </p>
                <p className="text-gray-300 text-sm leading-relaxed">{IC_BUNDLE.lockedBody}</p>
                <IcDiligenceBundlePitch variant="compact" showWhy={false} />
                <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                  {!alreadyOwnsCheckout('partner') && (
                    <button
                      type="button"
                      onClick={() => goCheckout('partner')}
                      className="px-4 py-3 min-h-[48px] rounded-lg border border-amber-500/50 bg-amber-500/10 hover:bg-amber-500/20 text-amber-100 font-bold text-sm"
                    >
                      Start Estimator / Permit Runner — $79/mo
                    </button>
                  )}
                  {!alreadyOwnsCheckout('contractor_pro') && (
                    <button
                      type="button"
                      onClick={() => goCheckout('contractor_pro')}
                      className="px-4 py-3 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm"
                    >
                      {HABIT_TIERS.contractor_pro.name} — $149/mo
                    </button>
                  )}
                  {!alreadyOwnsCheckout('ic_project') && (
                    <button
                      type="button"
                      onClick={() => goCheckout('ic_project')}
                      className="px-4 py-3 min-h-[48px] rounded-lg border border-emerald-500/50 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-100 font-bold text-sm"
                    >
                      {IC_BUNDLE.ctaBuy}
                    </button>
                  )}
                </div>
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <a
                href="/orders?from=results"
                className="inline-flex px-4 py-2.5 min-h-[44px] items-center rounded-lg border border-emerald-400/50 bg-slate-950/40 hover:bg-slate-900 text-emerald-100 text-sm font-semibold"
              >
                My Orders (re-download / forward)
              </a>
              <a
                href="/jobs"
                className="inline-flex px-4 py-2.5 min-h-[44px] items-center rounded-lg border border-slate-500 bg-slate-900/60 hover:bg-slate-800 text-white text-sm font-semibold"
              >
                My Jobs
              </a>
            </div>
          </div>

          <SendResultsForm
            researchId={effectiveResearchId}
            summary={summary}
            analysis={view}
            defaultEmail={defaultEmail}
            defaultPhone={defaultPhone}
          />

          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-emerald-300/90 mb-1 flex items-center gap-2">
              <Share2 className="w-3.5 h-3.5" />
              Bid Risk Receipt — default bid-file forward
            </p>
            <p className="text-sm text-gray-300 mb-3">
              Forward or Download from the top of these results — or use the buttons below.
            </p>
            {(view.regguard_stamp?.grade || view.stamp_grade) && (
              <div
                className={`mb-3 rounded-lg border p-3 ${
                  (view.regguard_stamp?.grade || view.stamp_grade) === 'FAIL'
                    ? 'border-amber-500/55 bg-amber-500/10'
                    : (view.regguard_stamp?.grade || view.stamp_grade) === 'CAUTION'
                      ? 'border-amber-500/50 bg-amber-500/10'
                      : 'border-emerald-500/50 bg-emerald-500/10'
                }`}
              >
                <p className="text-lg font-black text-white tracking-tight">
                  {view.regguard_stamp?.label ||
                    ((view.regguard_stamp?.grade || view.stamp_grade) === 'FAIL'
                      ? 'REGGUARD STAMP: HOLD — high pre-bid risk'
                      : `REGGUARD STAMP: ${view.stamp_grade}`)}
                </p>
                <p className="text-xs text-sky-200/95 mt-2 leading-relaxed border border-sky-400/30 rounded-md bg-sky-950/40 px-2.5 py-2">
                  {(view.regguard_stamp?.headline ||
                    view.project_info?.address ||
                    'This site') +
                    ' — treat municipal permits and utility interconnection as parallel clocks until both are confirmed. See Executive summary above for contingency and drivers.'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  CLEAR = no Critical killers on the current pack · CAUTION = material risk · HOLD =
                  resolve drivers before treating the bid as clear. Not a credit rating or AHJ
                  rejection.
                </p>
                {view.regguard_stamp?.headline ? (
                  <p className="text-sm text-gray-200 mt-2">{view.regguard_stamp.headline}</p>
                ) : null}
                {view.regguard_stamp?.is_stale && view.regguard_stamp?.stale_reason ? (
                  <p className="text-xs text-amber-100 mt-2 border border-amber-400/40 rounded p-2">
                    STALE — {view.regguard_stamp.stale_reason}
                  </p>
                ) : null}
                <ul className="mt-2 space-y-1">
                  {(view.regguard_stamp?.drivers || []).slice(0, 3).map((d) => (
                    <li key={d.label} className="text-xs text-gray-300">
                      <span className="font-semibold text-white">
                        [{formatStampSeverity(d.severity)}]
                      </span>{' '}
                      {d.label}
                      {d.detail ? ` — ${d.detail}` : ''}
                    </li>
                  ))}
                </ul>
                <p className="text-[11px] text-gray-500 mt-2">
                  Valid until {view.regguard_stamp?.valid_until || view.stamp_valid_until || '—'}
                  {view.regguard_stamp?.fingerprint
                    ? ` · fp ${view.regguard_stamp.fingerprint}`
                    : ''}
                </p>
                {view.regguard_stamp?.disclaimer ? (
                  <p className="text-[11px] text-gray-500 mt-1">{view.regguard_stamp.disclaimer}</p>
                ) : null}
              </div>
            )}
            {view.regguard_stamp?.is_stale ? (
              <div className="mb-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-100">
                <p className="font-bold mb-1">Stamp is outdated — re-run before bid</p>
                <p className="text-xs text-amber-200/90 mb-2">
                  Local pack / AHJ fingerprint changed. Re-check before attaching or sharing the
                  Bid Risk Receipt. Day-7 re-run is preferred for LOI.
                </p>
                <button
                  type="button"
                  onClick={() => void runRecheck()}
                  disabled={recheckLoading}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold disabled:opacity-50"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  {recheckLoading ? 'Re-checking…' : 'Re-check site now'}
                </button>
              </div>
            ) : null}
            <p className="text-xs text-gray-400 mb-2">
              WhatsApp opens with the receipt text. Facebook/Instagram copy the caption — paste into your post.
              Link: <span className="text-emerald-300 break-all">{shareLink}</span>
            </p>
            <p className="text-[11px] text-gray-500 mb-2 leading-relaxed">
              <span className="text-gray-300 font-semibold">Lock stamp</span> freezes grade + fingerprint
              on this shared report so war-room edits cannot rewrite what was stamped — dispute-record
              integrity for you and the recipient. It is not a liability shield for Reg Guard. Seller
              protection lives in Terms: planning aid only, Unverified / confirm-with-AHJ labels, no
              invented fees, no sealed-bid / interconnection / geotech completeness claims, Stripe-handled
              payments (no cards stored in Reg Guard), and citeable pre-bid diligence — not a quote.
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void downloadBidReceipt()}
                disabled={packetLoading}
                className="inline-flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-black disabled:opacity-50"
              >
                <Download className="w-4 h-4" />
                {packetLoading ? 'Building…' : 'Download Receipt PDF'}
              </button>
              <button
                type="button"
                onClick={() => void forwardArtifact('Bid Risk Receipt')}
                className="inline-flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg border border-emerald-400/50 bg-emerald-500/15 text-emerald-100 text-sm font-bold"
              >
                <MessageSquare className="w-4 h-4" />
                Text receipt
              </button>
              <button
                type="button"
                onClick={() => void copyShareText('text')}
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg border border-purple-500/40 bg-purple-500/10 text-purple-200 text-sm font-semibold hover:bg-purple-500/20 transition"
              >
                {copied === 'text' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                {copied === 'text' ? 'Copied receipt' : 'Copy forward text'}
              </button>
              <button
                type="button"
                onClick={() => void freezeWarRoomStamp()}
                disabled={!effectiveResearchId}
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg bg-white/10 border border-white/20 text-gray-200 text-sm font-semibold disabled:opacity-50"
                title="Locks stamp grade + fingerprint on this shared report so later edits cannot rewrite what was stamped"
              >
                Lock stamp
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
                onClick={() => setSharePreviewOpen((v) => !v)}
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg border border-slate-600 bg-slate-800/80 text-gray-200 text-sm font-semibold hover:bg-slate-700 transition"
              >
                {sharePreviewOpen ? 'Hide share text' : 'Show share text'}
              </button>
            </div>
            {sharePreviewOpen && (
              <textarea
                readOnly
                value={shareText}
                onFocus={(e) => e.currentTarget.select()}
                className="mt-3 w-full min-h-[140px] rounded-lg border border-slate-600 bg-slate-900 text-gray-200 text-xs p-3 font-mono"
                aria-label={shareTitle || 'Share text for Instagram Facebook or copy'}
              />
            )}
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
            Outputs are planning aids — confirm with AHJ before bid. Citeable pre-bid diligence, not a quote
            or sealed bid. Forward only what you can defend.
          </p>

          {/* Bid Risk Receipt — forwardable hero */}
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
                    Site-specific CYA stamp: contingency + top risks. Citeable pre-bid diligence —
                    planning aid, not a quote, sealed bid, or AHJ filing.
                    {view.dc_positioning ? ' Parallel AHJ + utility clocks (not an interconnection study).' : ''}
                  </p>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => void downloadBidReceipt()}
                    disabled={packetLoading}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-black disabled:opacity-50"
                  >
                    <Download className="w-4 h-4" />
                    {packetLoading ? 'Building…' : 'Download Receipt PDF'}
                  </button>
                  <button
                    type="button"
                    onClick={() => void forwardArtifact('Bid Risk Receipt')}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg border border-emerald-400/50 text-emerald-100 text-sm font-bold"
                  >
                    <MessageSquare className="w-4 h-4" />
                    Text receipt
                  </button>
                  <button
                    type="button"
                    onClick={() => void copyShareText('text')}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg bg-white/10 border border-white/20 text-white text-sm font-semibold"
                  >
                    <Copy className="w-4 h-4" />
                    Copy forward text
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!allowProDeskDownloads) {
                        showToast(proDeskGateMessage('bid_sheet_csv'));
                        goCheckout('contractor_pro');
                        return;
                      }
                      void downloadBidSheetCsv();
                    }}
                    disabled={packetLoading}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] rounded-lg border border-blue-400/40 text-blue-100 text-sm font-semibold disabled:opacity-50"
                  >
                    {allowProDeskDownloads ? 'Punch / fees CSV' : 'CSV — Pro $149'}
                  </button>
                </div>
              </div>
              <p className="text-xs text-gray-400 mb-2">
                {view.project_info?.address || 'Site'} · {view.ahj_card?.name || 'Local AHJ'}
              </p>
              {view.contingency_band && (
                <div className="relative mb-1">
                  <p
                    className={`text-4xl font-black text-emerald-400 tracking-tight ${
                      softLocked ? 'blur-md select-none' : ''
                    }`}
                  >
                    +{view.contingency_band.pct_low}% – +{view.contingency_band.pct_high}%
                  </p>
                  {softLocked ? (
                    <p className="text-xs text-purple-100 mt-2 font-semibold">
                      Free — forward the receipt or upgrade to reveal the contingency band.
                    </p>
                  ) : null}
                </div>
              )}
              {view.contingency_band && (
                <p
                  className={`text-sm text-gray-300 mb-3 ${
                    softLocked ? 'blur-sm select-none' : ''
                  }`}
                >
                  Suggested cushion on your base bid for this site (mid {view.contingency_band.pct_mid}
                  %). Add roughly {view.contingency_band.pct_low}%–{view.contingency_band.pct_high}% for
                  AHJ fees, timeline slip, and local risk — planning aid, not a quote.
                </p>
              )}
              <p className="text-xs text-amber-100/95 mb-3 border border-amber-500/35 rounded-md px-2.5 py-2 bg-amber-500/10">
                Re-run before you submit the bid. Stamp valid until{' '}
                {(view.regguard_stamp?.valid_until || view.stamp_valid_until || 'this run')
                  .toString()
                  .slice(0, 10)}
                . Fees and portal asks move.
              </p>
              {!coverage.feesAllowed ? (
                <p className="text-xs text-amber-100/95 mb-3 border border-amber-500/35 rounded-md px-2.5 py-2 bg-amber-500/10">
                  This ZIP is not a full DFW/Austin pack — expect Unverified. Confirm every line with
                  the AHJ before you treat this as bid-ready.
                </p>
              ) : null}
              <ol className="space-y-2 list-decimal pl-5">
                {(view.margin_killers || []).slice(0, 3).map((k, i) => {
                  const href =
                    (k.source_url && /^https?:\/\//i.test(k.source_url) && k.source_url) ||
                    view.ahj_card?.fees_url ||
                    view.ahj_card?.portal_url ||
                    null;
                  const cta =
                    (k.source_label || '').trim() ||
                    (href ? 'Confirm with AHJ' : 'No portal link — confirm locally');
                  return (
                  <li key={`${k.title}-${i}`} className="text-sm text-gray-200">
                    <span className="text-amber-200 font-semibold text-xs uppercase mr-1">
                      {k.priority || 'NOTE'}
                    </span>
                    <span className="text-white font-medium">{k.title}</span>
                    {k.detail && (
                      <p
                        className={`text-gray-400 text-xs mt-0.5 line-clamp-2 ${
                          softLocked ? 'blur-sm select-none' : ''
                        }`}
                      >
                        {k.detail}
                      </p>
                    )}
                    {k.planning_exposure?.usd_mid != null && (
                      <p
                        className={`text-emerald-300/90 text-xs mt-1 ${
                          softLocked || blurProDesk ? 'blur-sm select-none' : ''
                        }`}
                      >
                        Planning exposure ~$
                        {Number(k.planning_exposure.usd_low || 0).toLocaleString()}–$
                        {Number(k.planning_exposure.usd_high || 0).toLocaleString()} — not
                        guaranteed savings
                      </p>
                    )}
                    {href ? (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1.5 px-3 py-2 min-h-[40px] rounded-md text-xs font-bold uppercase tracking-wide bg-emerald-600 hover:bg-emerald-500 text-white"
                      >
                        ↗ {cta}
                      </a>
                    ) : (
                      <CitationBadge
                        verified={false}
                        source_label={cta}
                      />
                    )}
                  </li>
                  );
                })}
              </ol>
              {showDemandFeedback && !demandFeedbackSent ? (
                <div className="mt-4 pt-3 border-t border-emerald-500/25 space-y-2">
                  <p className="text-xs text-gray-300 font-medium">
                    One-tap: would you forward this receipt into a real bid file?
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      ['would_forward', 'Yes — I’d forward it'],
                      ['missing_fees', 'Missing fees / gotchas'],
                      ['dont_trust', 'Don’t trust it yet'],
                    ].map(([ans, label]) => (
                      <button
                        key={ans}
                        type="button"
                        onClick={() => sendDemandFeedback(ans)}
                        className="px-3 py-1.5 rounded-lg border border-emerald-500/40 bg-slate-950/40 text-xs text-emerald-100 hover:bg-emerald-500/20"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
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

          {/* Coverage — Full city pack always jumps to curated fees + gotchas */}
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
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => void downloadCityPackPdf()}
                disabled={packetLoading}
                className={`inline-flex items-center gap-2 px-3 py-2 min-h-[40px] rounded-lg text-xs font-bold tracking-wide border disabled:opacity-60 ${
                  coverage.tier === 'full_pack' || coverage.tier === 'paid_local'
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-400/50'
                    : 'bg-slate-800 hover:bg-slate-700 text-gray-100 border-slate-500'
                }`}
                title="Download Full city pack PDF — contingency, fees, gotchas, AHJ links"
              >
                <Download className="w-3.5 h-3.5" />
                {packetLoading ? 'Building city pack…' : 'Download Full city pack PDF'}
              </button>
              <p className="text-sm text-gray-200 flex-1 min-w-[12rem]">{coverage.warning}</p>
              <button
                type="button"
                className="inline-flex items-center gap-2 px-3 py-2 min-h-[40px] rounded-lg border border-emerald-500/40 bg-slate-950/40 hover:bg-slate-900 text-emerald-100 text-xs font-bold"
                onClick={jumpToCityPack}
              >
                Jump to Full city pack
              </button>
            </div>
            {view.paid_local?.status === 'capped' && (
              <p className="text-sm text-amber-200 mt-3" role="status">
                {view.paid_local.user_message ||
                  'Daily paid scrape cap reached. Showing federal/state + pack/cache. Try again tomorrow or use an IC Project for heavy research.'}
              </p>
            )}
          </section>

          {/* Free: share-to-unlock / paid deepen only — paid CTAs live in primary upgrade below (F1) */}
          {!isDeep && (canUnlockDeeper || softLocked) && (
            <section className="rounded-xl border border-amber-500/30 bg-gradient-to-br from-amber-500/10 via-slate-900/80 to-emerald-500/10 p-4 sm:p-5">
              <div className="flex items-start gap-3 mb-3">
                <Sparkles className="w-5 h-5 text-amber-300 shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white font-bold text-base">
                    {canUnlockDeeper
                      ? 'You are paid — unlock deeper research on this site'
                      : `Free preview — top ${FREE_PUNCH_VISIBLE} punch lines`}
                  </h3>
                  <p className="text-gray-300 text-sm mt-1">
                    {canUnlockDeeper
                      ? 'Re-run with your paid email for Contractor Pro local confirm + light scout (more citeable sources than free).'
                      : 'Forward this Bid Risk Receipt to unlock the rest of the free punch list — or start Estimator / Permit Runner for more monthly lookups.'}
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
                    <button
                      type="button"
                      onClick={() => void downloadBidReceipt()}
                      disabled={packetLoading}
                      className="px-4 py-3 min-h-[48px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm disabled:opacity-60"
                    >
                      {packetLoading ? 'Building receipt…' : 'Forward Bid Risk Receipt — unlock full free list'}
                    </button>
                    <button
                      type="button"
                      onClick={() => void copyShareText('text')}
                      className="px-4 py-3 min-h-[48px] rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold text-sm"
                    >
                      Copy receipt text
                    </button>
                    {!alreadyOwnsCheckout('partner') && (
                      <button
                        type="button"
                        onClick={() => goCheckout('partner')}
                        className="px-4 py-3 min-h-[48px] rounded-lg border border-amber-500/50 bg-amber-500/10 hover:bg-amber-500/20 text-amber-100 font-bold text-sm"
                      >
                        Start Estimator / Permit Runner — $79/mo
                      </button>
                    )}
                  </>
                )}
              </div>
            </section>
          )}

          {/* Local gotchas render inside Full city pack (#rg-city-pack) so Jump lands on them */}

          {/* F1: exactly one primary paid CTA for this results view */}
          {renderPrimaryUpgrade()}

          {(() => {
            const brief = extractScoutBriefing(view.pro_summary_markdown);
            if (!isDeep || !brief) return null;
            return (
              <section className="rounded-xl border border-amber-500/35 bg-slate-950/80 p-4 sm:p-5">
                <p className="text-[11px] font-black uppercase tracking-[0.16em] text-amber-200">
                  Scout briefing
                </p>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Action items are on the pre-bid punch list below. This card is only the watchdog
                  and close-out — not a second punch list.
                </p>
                {brief.watchdog ? (
                  <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-3">
                    <p className="text-xs font-bold uppercase tracking-wide text-amber-100">
                      Code-change watchdog
                    </p>
                    <p className="text-sm text-gray-100 mt-1.5 leading-relaxed">{brief.watchdog}</p>
                    {brief.hits.length > 0 ? (
                      <ul className="mt-2 space-y-1">
                        {brief.hits.map((hit) => (
                          <li key={hit} className="text-xs text-gray-300 leading-relaxed">
                            {hit}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
                {brief.bottomLine ? (
                  <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-3">
                    <p className="text-xs font-bold uppercase tracking-wide text-emerald-200">
                      Bottom line
                    </p>
                    <p className="text-sm text-gray-100 mt-1.5 leading-relaxed">{brief.bottomLine}</p>
                  </div>
                ) : null}
                {brief.note && !brief.watchdog && !brief.bottomLine ? (
                  <p className="text-sm text-gray-200 mt-3 leading-relaxed">{brief.note}</p>
                ) : null}
              </section>
            );
          })()}

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
                  Ranked Critical → Low. Coverage:{' '}
                  <span className="text-gray-200 font-semibold">{coverage.badge}</span>
                  {!coverage.feesAllowed
                    ? ' — fee dollars not shown; open the AHJ portal to confirm.'
                    : ' — confirm fee dollars on the official schedule.'}
                </p>
                {(() => {
                  const ranked = rankedPunchItems(view).slice(0, punchVisible);
                  let lastPri = '';
                  return ranked.map((item, idx) => {
                    const pri = (item.priority || 'MEDIUM').toUpperCase();
                    const showHeader = pri !== lastPri;
                    lastPri = pri;
                    return (
                      <div key={`pl-${idx}`}>
                        {showHeader && (
                          <p className="text-[11px] font-bold uppercase tracking-wide text-gray-500 px-1 pt-2 pb-1">
                            {pri}
                          </p>
                        )}
                        <div
                          className={`rounded-lg p-3 border ${
                            pri === 'CRITICAL'
                              ? 'bg-red-900/20 border-red-500/30'
                              : 'bg-slate-800/50 border-slate-700/50'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <p className="text-white text-sm font-semibold min-w-0 flex-1">{item.task}</p>
                            <PriorityChip priority={item.priority} />
                          </div>
                          <p className="text-xs text-gray-400">
                            {item.timeline} • {item.responsible_party}
                            {!softLocked && item.estimated_cost != null && item.estimated_cost > 0
                              ? ` • $${item.estimated_cost.toLocaleString()}`
                              : ''}
                          </p>
                          {!softLocked || item.verified || item.source_url ? (
                            <CitationBadge
                              source_url={item.source_url}
                              source_label={item.source_label}
                              verified={item.verified}
                              cost_verified={item.cost_verified}
                              estimated_cost={softLocked ? undefined : item.estimated_cost}
                            />
                          ) : (
                            <p className="text-[11px] text-amber-200/80 mt-1">
                              Unverified — confirm with AHJ
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  });
                })()}
                {softLocked && (view.punch_list?.punch_list || []).length > punchVisible && (
                  <div className="space-y-2">
                    {(view.punch_list?.punch_list || [])
                      .slice(punchVisible, punchVisible + 3)
                      .map((item, idx) => (
                        <div
                          key={`blur-punch-${idx}`}
                          className="relative overflow-hidden rounded-lg border border-purple-500/30 bg-slate-800/40 p-3 select-none"
                          aria-hidden
                        >
                          <div className="blur-sm opacity-70 pointer-events-none">
                            <p className="text-white text-sm font-semibold">{item.task}</p>
                            <p className="text-xs text-gray-400 mt-1">
                              {item.timeline} • {item.responsible_party || 'Owner'}
                            </p>
                          </div>
                          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/55">
                            <span className="text-[11px] font-bold uppercase tracking-wide text-purple-100 px-2 py-1 rounded bg-purple-600/40 border border-purple-400/40">
                              Locked
                            </span>
                          </div>
                        </div>
                      ))}
                    <div className="rounded-lg border border-dashed border-purple-500/40 bg-purple-500/10 p-4 text-center">
                      <p className="text-sm text-purple-100 mb-3">
                        {(view.punch_list?.punch_list || []).length - punchVisible} more punch
                        lines locked — forward the Bid Risk Receipt or upgrade to unlock.
                      </p>
                      {demoTier ? (
                        <p className="text-xs text-purple-200/90">
                          SAMPLE — Free shows the least. Estimator unlocks more. Pro unlocks the desk.
                        </p>
                      ) : (
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
                          {!alreadyOwnsCheckout('partner') && (
                            <button
                              type="button"
                              onClick={() => goCheckout('partner')}
                              className="px-4 py-2 rounded-lg border border-amber-500/50 bg-amber-500/10 hover:bg-amber-500/20 text-amber-100 text-sm font-bold"
                            >
                              Estimator / Permit Runner — $79/mo
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
                {proBlurPunchTeasers > 0 &&
                  (view.punch_list?.punch_list || []).length > punchVisible && (
                    <div className="space-y-2 mt-2">
                      {(view.punch_list?.punch_list || [])
                        .slice(punchVisible, punchVisible + proBlurPunchTeasers)
                        .map((item, idx) => (
                          <div
                            key={`blur-partner-${idx}`}
                            className="relative overflow-hidden rounded-lg border border-amber-500/30 bg-slate-800/40 p-3 select-none"
                            aria-hidden
                          >
                            <div className="blur-sm opacity-70 pointer-events-none">
                              <p className="text-white text-sm font-semibold">{item.task}</p>
                              <p className="text-xs text-gray-400 mt-1">Pro desk line…</p>
                            </div>
                            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/55">
                              <span className="text-[11px] font-bold uppercase tracking-wide text-amber-100 px-2 py-1 rounded bg-amber-600/40 border border-amber-400/40">
                                Contractor Pro
                              </span>
                            </div>
                          </div>
                        ))}
                      <p className="text-xs text-amber-100/90 text-center border border-amber-500/30 rounded-lg px-3 py-2 bg-amber-500/10">
                        {demoTier
                          ? 'SAMPLE — Estimator unlocks punch + receipt. City pack / CSV / bid packet stay on Contractor Pro.'
                          : 'Estimator / Permit Runner unlocks punch + receipt. City pack / CSV / bid packet unlock on Contractor Pro ($149).'}
                      </p>
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
                {view.summary?.estimated_timeline || 'Confirm with AHJ'}
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
                    ${(view.summary?.estimated_total_cost || 0).toLocaleString()}
                  </p>
                  <CitationBadge
                    verified={Boolean(view.punch_list?.estimates_verified)}
                    cost_verified={Boolean(view.punch_list?.estimates_verified)}
                    estimated_cost={view.summary?.estimated_total_cost}
                    source_label="Rollup of line items"
                  />
                </>
              )}
            </div>
          </div>

          {/* City pack — one contiguous section: header + all subsections */}
          <section
            id="rg-city-pack"
            className="scroll-mt-6 rounded-xl border border-emerald-500/35 bg-emerald-500/[0.07] overflow-hidden"
          >
            <div className="px-4 py-3 border-b border-emerald-500/25 bg-emerald-500/10 flex flex-wrap items-start justify-between gap-2">
              <div>
              <p className="text-sm font-bold text-emerald-200">
                Full city pack
                {view.ahj_card?.name || view.project_info?.city || view.local_pack?.city
                  ? ` — ${view.ahj_card?.name || view.project_info?.city || view.local_pack?.city}`
                  : ''}
                {view.project_info?.state || view.local_pack?.state
                  ? `, ${view.project_info?.state || view.local_pack?.state}`
                  : ''}
              </p>
              <p className="text-xs text-gray-300 mt-1 leading-relaxed">
                {packFees.length || packGotchas.length || view.contingency_band
                  ? `${packFees.length} fee line${packFees.length === 1 ? '' : 's'} · ${packGotchas.length} gotcha${packGotchas.length === 1 ? '' : 's'}${view.contingency_band ? ` · contingency +${view.contingency_band.pct_low}–${view.contingency_band.pct_high}%` : ''}. Download this pack as a PDF, or use the bid downloads below.`
                  : 'Download the Full city pack PDF: curated fees, gotchas, contingency, AHJ links, and inspections (planning aids — confirm dollars on the official schedule before bid).'}
              </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  if (!allowProDeskDownloads) {
                    showToast(proDeskGateMessage('city_pack_pdf'));
                    goCheckout('contractor_pro');
                    return;
                  }
                  void downloadCityPackPdf();
                }}
                disabled={packetLoading}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold disabled:opacity-50 min-h-[44px] shrink-0"
              >
                <Download className="w-4 h-4" />
                {packetLoading
                  ? 'Building…'
                  : allowProDeskDownloads
                    ? 'Download PDF'
                    : 'PDF — Pro $149'}
              </button>
            </div>

            {cityPackHasBody ? (
              <div id="bid-arbitrage" className="divide-y divide-emerald-500/20 relative">
                {softLocked ? (
                  <div className="absolute inset-0 z-10 pointer-events-none flex flex-col justify-end">
                    <div className="absolute inset-0 backdrop-blur-[6px] bg-slate-950/50" />
                    <div className="relative z-10 m-4 rounded-lg border border-purple-500/40 bg-purple-500/15 px-3 py-2.5 text-center pointer-events-auto">
                      <p className="text-xs font-bold text-purple-50">
                        Free — city pack fees & gotchas blurred. Forward the receipt or upgrade to
                        Estimator for more punch; Contractor Pro unlocks the full pack.
                      </p>
                      {!demoTier ? (
                        <button
                          type="button"
                          onClick={() => goCheckout('partner')}
                          className="mt-2 px-3 py-1.5 rounded-md bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold"
                        >
                          Estimator / Permit Runner — $79
                        </button>
                      ) : null}
                    </div>
                  </div>
                ) : blurProDesk ? (
                  <div className="px-4 py-3 border-b border-amber-500/30 bg-amber-500/10">
                    <p className="text-xs font-bold text-amber-50">
                      Estimator — contingency & punch unlocked. Fee dollars and pack PDF stay on
                      Contractor Pro ($149).
                    </p>
                    {!demoTier ? (
                      <button
                        type="button"
                        onClick={() => goCheckout('contractor_pro')}
                        className="mt-2 px-3 py-1.5 rounded-md bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold"
                      >
                        Unlock Contractor Pro
                      </button>
                    ) : null}
                  </div>
                ) : null}
                {view.contingency_band && (
                  <div className="px-4 py-4">
                    <h4 className="text-sm font-bold text-emerald-300 mb-2">
                      {view.contingency_band.label || 'Suggested contingency'}
                    </h4>
                    <p className="text-2xl font-black text-emerald-400">
                      {view.contingency_band.pct_low}% – {view.contingency_band.pct_high}%
                      <span className="text-base font-semibold text-gray-300 ml-2">
                        (mid {view.contingency_band.pct_mid}%)
                      </span>
                    </p>
                    {typeof view.contingency_band.usd_mid === 'number' && !softLocked && !blurProDesk && (
                      <p className="text-sm text-gray-300 mt-1">
                        ~${view.contingency_band.usd_mid.toLocaleString()} mid band on current rollup
                      </p>
                    )}
                    {typeof view.contingency_band.usd_mid === 'number' && blurProDesk && !softLocked && (
                      <p className="text-sm text-amber-100/80 mt-1">
                        Dollar mid-band unlocks on Contractor Pro.
                      </p>
                    )}
                    <p className="text-gray-500 text-xs mt-2">{view.contingency_band.disclaimer}</p>
                    <CitationBadge verified={false} source_label="Heuristic — not a quote" />
                  </div>
                )}

                {packFees.length > 0 && (
                  <div className="px-4 py-4">
                    <h4 className="text-sm font-bold text-blue-300 mb-2">
                      {view.fee_card?.title || 'Fee & timeline extract'}
                      {(view.fee_card?.planning_aid || view.fee_card?.paid_local_confirm) && (
                        <span className="ml-2 text-xs font-semibold text-amber-300">Planning aid</span>
                      )}
                    </h4>
                    <p className="text-[11px] text-amber-200/90 mb-2">
                      Permit ≠ tap ≠ impact. Mixing these is how bids get blown — each line is labeled.
                    </p>
                    <p className="text-white text-sm mb-2">
                      Timeline: {view.fee_card?.timeline || view.summary?.estimated_timeline || 'Confirm with AHJ'}
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
                        {packFees.slice(0, 10).map((f, i) => (
                          <li key={i} className="text-sm text-gray-300">
                            {(() => {
                              const kind = classifyFeeKind(f.label, f.detail, f.trade);
                              return (
                                <span
                                  title={feeKindHint(kind)}
                                  className="mr-2 inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-amber-500/15 text-amber-200 border border-amber-500/30"
                                >
                                  {kind}
                                </span>
                              );
                            })()}
                            {f.trade && (
                              <span className="mr-2 inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-slate-700 text-blue-200">
                                {f.trade}
                              </span>
                            )}
                            <span className="text-white font-medium">{f.label}</span>
                            {typeof f.amount_usd === 'number' ? (
                              <span
                                className={
                                  softLocked || blurProDesk ? 'blur-sm select-none inline-block' : undefined
                                }
                              >
                                {` — $${f.amount_usd.toLocaleString()}`}
                              </span>
                            ) : f.amount_requires_schedule ? (
                              ' — confirm on schedule'
                            ) : (
                              ''
                            )}
                            {(f.planning_aid ||
                              view.fee_card?.planning_aid ||
                              view.fee_card?.paid_local_confirm) && (
                              <span className="ml-1 text-xs text-amber-300/90">(planning aid)</span>
                            )}
                            <CitationBadge
                              verified={Boolean(f.verified)}
                              source_url={f.source_url || f.citation_url}
                              source_label={f.source_label || f.citation_note || 'Confirm with AHJ'}
                            />
                          </li>
                        ))}
                      </ul>
                    )}
                    {(view.fee_card?.disclaimer ||
                      view.fee_card?.paid_local_confirm ||
                      view.fee_card?.planning_aid) && (
                      <p className="text-amber-200/80 text-xs mt-2">
                        {view.fee_card?.disclaimer ||
                          'Planning aid only — not an AHJ quote. Confirm on the official fee schedule before bid.'}
                      </p>
                    )}
                  </div>
                )}

                {packGotchas.length > 0 && (
                  <div id="rg-local-gotchas" className="px-4 py-4 space-y-3">
                    <h4 className="text-sm font-bold text-amber-200">
                      {view.gotcha_watchlist?.title || 'Local gotcha watchlist'}
                    </h4>
                    <ul className="space-y-3">
                      {packGotchas.slice(0, 8).map((g) => (
                        <li key={g.id || g.title} className="text-sm text-gray-300">
                          <span className="text-amber-200 font-semibold text-xs uppercase mr-1.5">
                            {formatStampSeverity(g.priority)}
                          </span>
                          <span className="text-white font-medium">{g.title}</span>
                          {g.detail ? <p className="text-gray-400 text-xs mt-1">{g.detail}</p> : null}
                          {(g.source_url || g.source_label) && (
                            <CitationBadge
                              verified={Boolean(g.source_url)}
                              source_url={g.source_url}
                              source_label={g.source_label || 'AHJ source'}
                            />
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {view.ahj_card && (
                  <div className="px-4 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <h4 className="text-sm font-bold text-emerald-300">
                        {view.ahj_card.title || 'AHJ portal & contact'}
                      </h4>
                      {view.ahj_card.last_verified && (
                        <span className="text-xs font-semibold text-emerald-200/90">
                          Verified {view.ahj_card.last_verified}
                        </span>
                      )}
                    </div>
                    <p className="text-white font-semibold">{view.ahj_card.name}</p>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
                      {view.ahj_card.portal_url && (
                        <a
                          href={view.ahj_card.portal_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-purple-300 underline"
                        >
                          Portal
                        </a>
                      )}
                      {view.ahj_card.fees_url && (
                        <a
                          href={view.ahj_card.fees_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-purple-300 underline"
                        >
                          Fees
                        </a>
                      )}
                      {view.ahj_card.apply_url && (
                        <a
                          href={view.ahj_card.apply_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-purple-300 underline"
                        >
                          Apply
                        </a>
                      )}
                      {view.ahj_card.inspections_url && (
                        <a
                          href={view.ahj_card.inspections_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-purple-300 underline"
                        >
                          Inspections
                        </a>
                      )}
                    </div>
                    {view.ahj_card.notes && (
                      <p className="text-gray-400 text-xs mt-2">{view.ahj_card.notes}</p>
                    )}
                  </div>
                )}

                {view.inspection_sequence_card &&
                  (view.inspection_sequence_card.steps || []).length > 0 && (
                    <div className="px-4 py-4">
                      <h4 className="text-sm font-bold text-indigo-300 mb-2">
                        {view.inspection_sequence_card.title || 'Inspection sequence'}
                      </h4>
                      <ol className="list-decimal pl-5 space-y-1">
                        {(view.inspection_sequence_card.steps || []).map((step, i) => (
                          <li key={i} className="text-sm text-gray-200">
                            {step}
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}

                <div className="px-4 py-4 flex flex-col gap-3">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <div>
                      <h3 className="text-base font-bold text-white">Bid-time downloads</h3>
                      <p className="text-xs text-gray-400 mt-0.5">
                        Download PDFs here, or Text a share link — recipients open the link to view /
                        download. SMS cannot attach PDF files from the browser.
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {!allowProDeskDownloads && (
                      <p className="w-full text-xs text-amber-100/90 border border-amber-500/30 rounded-lg px-3 py-2 bg-amber-500/10">
                        Estimator / Permit Runner ($79): Receipt + punch + Saved Jobs. City pack PDF,
                        bid sheet CSV/PDF, and bid packet unlock on Contractor Pro ($149).
                      </p>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        if (!allowProDeskDownloads) {
                          showToast(proDeskGateMessage('city_pack_pdf'));
                          goCheckout('contractor_pro');
                          return;
                        }
                        void downloadCityPackPdf();
                      }}
                      disabled={packetLoading}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold disabled:opacity-50 min-h-[44px]"
                    >
                      <Download className="w-4 h-4" />
                      {packetLoading
                        ? 'Building…'
                        : allowProDeskDownloads
                          ? 'Full city pack PDF'
                          : 'City pack — Pro $149'}
                    </button>
                    <button
                      type="button"
                      onClick={() => void forwardArtifact('Full city pack PDF')}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-emerald-400/40 text-emerald-100 text-sm font-semibold min-h-[44px]"
                    >
                      <MessageSquare className="w-4 h-4" />
                      Text city pack
                    </button>
                    <button
                      type="button"
                      onClick={() => void downloadBidReceipt()}
                      disabled={packetLoading}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 border border-emerald-400/40 text-emerald-100 text-sm font-semibold disabled:opacity-50 min-h-[44px]"
                    >
                      <Download className="w-4 h-4" />
                      {packetLoading ? 'Building…' : 'Download Receipt PDF'}
                    </button>
                    <button
                      type="button"
                      onClick={() => void forwardArtifact('Bid Risk Receipt PDF')}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-emerald-400/40 text-emerald-100 text-sm font-semibold min-h-[44px]"
                    >
                      <MessageSquare className="w-4 h-4" />
                      Text receipt
                    </button>
                    <button
                      type="button"
                      onClick={() => void downloadBidSheetPdf()}
                      disabled={packetLoading}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold disabled:opacity-50 min-h-[44px]"
                    >
                      <Download className="w-4 h-4" />
                      Bid sheet PDF
                    </button>
                    <button
                      type="button"
                      onClick={() => void forwardArtifact('Bid Sheet PDF')}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-blue-400/40 text-blue-100 text-sm font-semibold min-h-[44px]"
                    >
                      <MessageSquare className="w-4 h-4" />
                      Text bid sheet
                    </button>
                    <button
                      type="button"
                      onClick={() => void downloadBidSheetCsv()}
                      disabled={packetLoading}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 border border-blue-400/40 text-blue-100 text-sm font-semibold disabled:opacity-50 min-h-[44px]"
                    >
                      Bid sheet CSV
                    </button>
                    <button
                      type="button"
                      onClick={() => void downloadBidPacketFull()}
                      disabled={packetLoading}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 border border-emerald-400/40 text-emerald-100 text-sm font-semibold disabled:opacity-50 min-h-[44px]"
                    >
                      Full Bid Packet PDF
                    </button>
                    <button
                      type="button"
                      onClick={() => void forwardArtifact('Full Bid Packet PDF')}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-emerald-400/40 text-emerald-100 text-sm font-semibold min-h-[44px]"
                    >
                      <MessageSquare className="w-4 h-4" />
                      Text bid packet
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
                  <div className="px-4 py-4 text-sm text-amber-100 bg-amber-500/10">
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

                <div className="px-4 py-4 space-y-2">
                  <h4 className="text-sm font-bold text-gray-200">Submit a local gotcha</h4>
                  <p className="text-xs text-gray-400">
                    Estimator / Permit Runner and Contractor Pro emails get a $20 credit after ops
                    verifies and cites the portal.
                  </p>
                  <textarea
                    value={gotchaText}
                    onChange={(e) => setGotchaText(e.target.value)}
                    rows={3}
                    placeholder="e.g. Plano rejects X if filed before Y…"
                    className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white"
                  />
                  <button
                    type="button"
                    disabled={gotchaBusy || !gotchaText.trim()}
                    className="px-3 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-sm font-bold disabled:opacity-50"
                    onClick={() => {
                      void (async () => {
                        const zip =
                          view.project_info?.zip ||
                          view.jurisdiction?.zip ||
                          view.coverage?.pack_key ||
                          '';
                        if (!zip || String(zip).length < 5) {
                          setGotchaMsg('Need a ZIP on this result to attach the note.');
                          return;
                        }
                        setGotchaBusy(true);
                        setGotchaMsg('');
                        try {
                          const body = new FormData();
                          body.set('zip_code', String(zip).slice(0, 5));
                          body.set('text', gotchaText.trim());
                          body.set('email', (defaultEmail || '').trim());
                          const res = await fetch(backendUrl('/community-gotchas'), {
                            method: 'POST',
                            body,
                          });
                          const data = await res.json().catch(() => ({}));
                          if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
                          setGotchaMsg(String(data.message || 'Saved.'));
                          setGotchaText('');
                        } catch (e) {
                          setGotchaMsg(e instanceof Error ? e.message : 'Submit failed');
                        } finally {
                          setGotchaBusy(false);
                        }
                      })();
                    }}
                  >
                    {gotchaBusy ? 'Sending…' : 'Submit gotcha'}
                  </button>
                  {gotchaMsg && <p className="text-xs text-amber-200">{gotchaMsg}</p>}
                </div>

                {view.document_checklist && (
                  <div className="px-4 py-4">
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
              </div>
            ) : (
              <p className="text-sm text-amber-100/90 px-4 py-3 leading-relaxed">
                This ZIP matched a city-pack badge, but fee/gotcha rows are not attached to this
                results payload yet. Open the AHJ portal links from coverage above, or re-run deep
                research with the pin confirmed.
              </p>
            )}
          </section>


          {/* Community friction signals */}
          {view.community_friction && (
            <section className="rounded-xl border border-slate-600 bg-slate-800/40 p-4 sm:p-5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-lg font-bold text-white">
                  {view.community_friction.title || 'Community friction signals'}
                </h3>
                <span className="text-xs font-bold uppercase tracking-wide text-amber-200 border border-amber-500/40 rounded px-2 py-1">
                  {view.community_friction.band || 'Heuristic'} · {view.community_friction.score ?? 0}/
                  {view.community_friction.score_max ?? 12}
                </span>
              </div>
              <p className="text-sm text-gray-300">
                {view.community_friction.headline}
              </p>
              <ul className="space-y-2">
                {(view.community_friction.signals || []).map((s) => (
                  <li
                    key={s.id || s.label}
                    className="text-sm text-gray-200 border border-slate-700/60 rounded-lg p-3"
                  >
                    <div className="flex justify-between gap-2 mb-1">
                      <span className="font-semibold">{s.label}</span>
                      <span className="text-xs text-gray-400">Level {s.level ?? 0}/3</span>
                    </div>
                    <p className="text-xs text-gray-400">{s.detail}</p>
                    {s.source_url ? (
                      <a
                        href={s.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-emerald-300 underline mt-1 inline-block"
                      >
                        Open source
                      </a>
                    ) : null}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-amber-200/90">{view.community_friction.disclaimer}</p>
            </section>
          )}

          {/* Data-center diligence cards */}
          {(view.parallel_clocks ||
            view.moratorium_radar ||
            view.power_path_card ||
            view.water_cooling_card ||
            view.opposition_card ||
            view.fast41_card ||
            view.vertical_playbook) && (
            <section className="rounded-xl border border-cyan-500/35 bg-cyan-950/30 p-4 sm:p-5 space-y-5">
              <div>
                <h3 className="text-lg font-bold text-white">
                  {view.dc_positioning?.headline || 'Data-center diligence'}
                </h3>
                {view.dc_positioning?.pitch ? (
                  <p className="text-sm text-gray-300 mt-1">{view.dc_positioning.pitch}</p>
                ) : null}
              </div>

              {view.vertical_playbook && (view.vertical_playbook.items || []).length > 0 ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h4 className="text-sm font-bold uppercase tracking-wide text-cyan-200">
                      {view.vertical_playbook.label || 'Vertical playbook'} — cite or Confirm
                    </h4>
                    <p className="text-xs text-cyan-100/90">
                      Checklist completeness:{' '}
                      <span className="font-bold text-white">
                        {view.vertical_playbook.stats?.completeness_pct ?? 0}%
                      </span>
                      <span className="text-gray-400">
                        {' '}
                        ({view.vertical_playbook.stats?.cited ?? 0} cited ·{' '}
                        {view.vertical_playbook.stats?.confirm ?? 0} confirm)
                      </span>
                    </p>
                  </div>
                  <p className="text-xs text-amber-200/90">
                    Completeness is checklist coverage with sources — not a guarantee. Confirm
                    fees and utility paths before bid.
                  </p>
                  {view.vertical_playbook.beachhead_hint ? (
                    <p className="text-xs text-gray-400">{view.vertical_playbook.beachhead_hint}</p>
                  ) : null}
                  <ul className="space-y-2">
                    {(view.vertical_playbook.items || []).map((it) => (
                      <li
                        key={it.id || it.task}
                        className="text-sm border border-slate-700/70 rounded-lg p-3 bg-slate-900/40"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded ${
                              it.status === 'cited'
                                ? 'bg-emerald-500/20 text-emerald-200'
                                : 'bg-amber-500/20 text-amber-100'
                            }`}
                          >
                            {it.status === 'cited' ? 'Cited' : 'Confirm'}
                          </span>
                          <span className="text-[10px] font-semibold text-gray-400">
                            [{it.priority}]
                          </span>
                          <span className="font-semibold text-white">{it.task}</span>
                        </div>
                        {it.detail ? (
                          <p className="text-xs text-gray-400 mt-1">{it.detail}</p>
                        ) : null}
                        {it.source_url ? (
                          <a
                            href={it.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-emerald-300 underline mt-1 inline-block"
                          >
                            {it.source_label || 'Open source'}
                          </a>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                  {view.vertical_playbook.disclaimer ? (
                    <p className="text-xs text-gray-500">{view.vertical_playbook.disclaimer}</p>
                  ) : null}
                </div>
              ) : null}

              {view.parallel_clocks && (
                <div className="space-y-2">
                  <h4 className="text-sm font-bold uppercase tracking-wide text-cyan-200">
                    {view.parallel_clocks.title || 'Parallel clocks'}
                  </h4>
                  <p className="text-sm text-gray-300">{view.parallel_clocks.headline}</p>
                  <ul className="space-y-2">
                    {(view.parallel_clocks.clocks || []).map((c) => (
                      <li
                        key={c.track || c.label}
                        className="text-sm border border-slate-700/70 rounded-lg p-3 bg-slate-900/40"
                      >
                        <p className="font-semibold text-white">{c.label}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {c.owner} · {c.status}
                        </p>
                        {c.url ? (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-emerald-300 underline mt-1 inline-block"
                          >
                            Open track
                          </a>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                  {view.parallel_clocks.disclaimer ? (
                    <p className="text-xs text-amber-200/80">{view.parallel_clocks.disclaimer}</p>
                  ) : null}
                </div>
              )}

              {view.moratorium_radar && (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="text-sm font-bold uppercase tracking-wide text-cyan-200">
                      {view.moratorium_radar.title || 'Moratorium radar'}
                    </h4>
                    {view.moratorium_radar.is_stale ? (
                      <span className="text-xs font-bold uppercase tracking-wide text-amber-100 border border-amber-400/50 rounded px-2 py-0.5">
                        Stale
                      </span>
                    ) : view.moratorium_radar.high_alert_state ? (
                      <span className="text-xs font-bold uppercase tracking-wide text-amber-100 border border-amber-400/50 rounded px-2 py-0.5">
                        High alert
                      </span>
                    ) : null}
                  </div>
                  {view.moratorium_radar.stale_banner ? (
                    <p className="text-xs text-amber-100 border border-amber-500/40 rounded-lg p-2">
                      {view.moratorium_radar.stale_banner}
                    </p>
                  ) : null}
                  <p className="text-sm text-gray-300">{view.moratorium_radar.headline}</p>
                  {view.moratorium_radar.updated ? (
                    <p className="text-xs text-gray-500">
                      Radar updated: {view.moratorium_radar.updated}
                      {typeof view.moratorium_radar.age_days === 'number'
                        ? ` (${view.moratorium_radar.age_days}d ago)`
                        : ''}
                    </p>
                  ) : null}
                  <ul className="space-y-2">
                    {(view.moratorium_radar.metros || []).slice(0, 4).map((m) => (
                      <li key={`${m.metro}-${m.state}`} className="text-xs text-gray-300">
                        <span className="font-semibold text-white">{m.metro}</span>
                        {m.status ? ` · ${m.status}` : ''}
                        {m.summary ? ` — ${m.summary}` : ''}
                        {m.citation_url ? (
                          <>
                            {' '}
                            <a
                              href={m.citation_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-emerald-300 underline"
                            >
                              cite
                            </a>
                          </>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                  {(view.moratorium_radar.bill_notes || []).slice(0, 2).map((n) => (
                    <p key={n.slice(0, 40)} className="text-xs text-amber-100/90">
                      {n.replace(/\*\*/g, '')}
                    </p>
                  ))}
                  {view.moratorium_radar.disclaimer ? (
                    <p className="text-xs text-amber-200/80">{view.moratorium_radar.disclaimer}</p>
                  ) : null}
                </div>
              )}

              {view.power_path_card && (
                <div className="space-y-2">
                  <h4 className="text-sm font-bold uppercase tracking-wide text-cyan-200">
                    {view.power_path_card.title || 'Power path'}
                  </h4>
                  <p className="text-sm text-gray-300">{view.power_path_card.headline}</p>
                  <p className="text-xs text-gray-400">
                    {typeof view.power_path_card.mw_hint === 'number'
                      ? `MW hint: ${view.power_path_card.mw_hint}`
                      : 'MW hint: not parsed'}
                    {view.power_path_card.fast41_candidate ? ' · FAST-41 candidate' : ''}
                  </p>
                  <ul className="list-disc pl-5 text-xs text-gray-300 space-y-1">
                    {(view.power_path_card.checklist || []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  {view.power_path_card.disclaimer ? (
                    <p className="text-xs text-amber-200/80">{view.power_path_card.disclaimer}</p>
                  ) : null}
                </div>
              )}

              {view.water_cooling_card && (
                <div className="space-y-2">
                  <h4 className="text-sm font-bold uppercase tracking-wide text-cyan-200">
                    {view.water_cooling_card.title || 'Water & cooling'}
                  </h4>
                  <p className="text-sm text-gray-300">{view.water_cooling_card.headline}</p>
                  <ul className="list-disc pl-5 text-xs text-gray-300 space-y-1">
                    {(view.water_cooling_card.checklist || []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  {(view.water_cooling_card.water_hits || [])
                    .concat(view.water_cooling_card.wue_hits || [])
                    .slice(0, 3)
                    .map((h) => (
                      <p key={h.title || h.url} className="text-xs text-gray-400">
                        {h.url ? (
                          <a
                            href={h.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-emerald-300 underline"
                          >
                            {h.title || 'Source'}
                          </a>
                        ) : (
                          h.title
                        )}
                        {h.snippet ? ` — ${h.snippet}` : ''}
                      </p>
                    ))}
                  {view.water_cooling_card.disclaimer ? (
                    <p className="text-xs text-amber-200/80">{view.water_cooling_card.disclaimer}</p>
                  ) : null}
                </div>
              )}

              {view.opposition_card && (
                <div className="space-y-2">
                  <h4 className="text-sm font-bold uppercase tracking-wide text-cyan-200">
                    {view.opposition_card.title || 'Opposition early-warning'}
                  </h4>
                  <p className="text-sm text-gray-300">{view.opposition_card.headline}</p>
                  {(view.opposition_card.hot_signals || []).slice(0, 3).map((s) => (
                    <p key={s.id || s.label} className="text-xs text-gray-300">
                      <span className="font-semibold text-white">{s.label}</span>
                      {s.detail ? ` — ${s.detail}` : ''}
                    </p>
                  ))}
                  {view.opposition_card.disclaimer ? (
                    <p className="text-xs text-amber-200/80">{view.opposition_card.disclaimer}</p>
                  ) : null}
                </div>
              )}

              {view.fast41_card && (
                <div className="space-y-2">
                  <h4 className="text-sm font-bold uppercase tracking-wide text-cyan-200">
                    {view.fast41_card.title || 'FAST-41'}
                  </h4>
                  <p className="text-sm text-gray-300">{view.fast41_card.headline}</p>
                  {view.fast41_card.federal_note ? (
                    <p className="text-xs text-gray-400">{view.fast41_card.federal_note}</p>
                  ) : null}
                  {view.fast41_card.conflict?.active && view.fast41_card.conflict.note ? (
                    <p className="text-xs text-amber-100 border border-amber-500/40 rounded-lg p-2">
                      {view.fast41_card.conflict.note.replace(/\*\*/g, '')}
                    </p>
                  ) : null}
                  {view.fast41_card.portal ? (
                    <a
                      href={view.fast41_card.portal}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-emerald-300 underline inline-block"
                    >
                      Permitting Council portal
                    </a>
                  ) : null}
                  {view.fast41_card.disclaimer ? (
                    <p className="text-xs text-amber-200/80">{view.fast41_card.disclaimer}</p>
                  ) : null}
                </div>
              )}

              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  className="text-xs font-semibold text-cyan-100 border border-cyan-500/40 rounded-lg px-3 py-1.5 hover:bg-cyan-500/10"
                  onClick={async () => {
                    try {
                      const res = await fetch(backendUrl('/dc/diligence-export'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ analysis: view }),
                      });
                      if (!res.ok) throw new Error('export failed');
                      const data = await res.json();
                      const blob = new Blob([JSON.stringify(data, null, 2)], {
                        type: 'application/json',
                      });
                      await downloadOnlyBlob(blob, 'RegGuard_DC_Diligence.json');
                    } catch {
                      /* soft fail */
                    }
                  }}
                >
                  Export DC diligence JSON
                </button>
                <a
                  href="/moratorium-radar"
                  className="text-xs font-semibold text-cyan-100 border border-cyan-500/40 rounded-lg px-3 py-1.5 hover:bg-cyan-500/10"
                >
                  Open moratorium radar
                </a>
              </div>
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
                <div className="rounded-lg border border-slate-600/60 bg-slate-800/40 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="font-bold text-white">Overall parcel GIS risk</span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-semibold ${
                        ['HIGH', 'CRITICAL'].includes(
                          String(view.environmental_screening?.risk_level || '').toUpperCase()
                        )
                          ? 'bg-red-500/20 text-red-200'
                          : ['MEDIUM', 'CAUTION'].includes(
                                String(view.environmental_screening?.risk_level || '').toUpperCase()
                              )
                            ? 'bg-amber-500/20 text-amber-200'
                            : ['LOW'].includes(
                                  String(view.environmental_screening?.risk_level || '').toUpperCase()
                                )
                              ? 'bg-emerald-500/20 text-emerald-200'
                              : 'bg-slate-600/40 text-gray-300'
                      }`}
                    >
                      {view.environmental_screening?.risk_score_hidden ||
                      ['UNKNOWN', 'UNAVAILABLE', 'PRELIMINARY', ''].includes(
                        String(view.environmental_screening?.risk_level || '').toUpperCase()
                      )
                        ? 'UNAVAILABLE — incomplete GIS'
                        : String(view.environmental_screening?.risk_level || 'UNKNOWN')}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    {view.environmental_screening?.risk_honesty_note ||
                      view.honesty?.labels?.risk ||
                      'Score uses verified FEMA flood + NWI wetlands only. Noise / NEPA / state do not set the overall score.'}
                  </p>
                </div>
                <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-3 text-sm text-cyan-50">
                  <p className="font-bold text-cyan-100 mb-1">Sites we scan for this section</p>
                  <p className="text-xs text-cyan-100/90 leading-relaxed mb-2">
                    Wetlands / species stay UNKNOWN when the pin GIS call fails or returns no
                    parcel hit — use the mapper links on each card, then re-check after confirming
                    lat/lng. Overall LOW requires both flood and wetlands to resolve.
                  </p>
                  <ul className="text-xs text-cyan-100/85 space-y-1 list-disc pl-4">
                    <li>
                      <a
                        className="underline hover:text-white"
                        href="https://www.fws.gov/program/national-wetlands-inventory/wetlands-mapper"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        USFWS NWI Wetlands Mapper
                      </a>{' '}
                      (+ USGS Wetlands MapServer query at the pin)
                    </li>
                    <li>
                      <a
                        className="underline hover:text-white"
                        href="https://ipac.ecosphere.fws.gov/"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        USFWS IPaC
                      </a>{' '}
                      — endangered species / critical habitat at the pin
                    </li>
                    <li>
                      <a
                        className="underline hover:text-white"
                        href="https://msc.fema.gov/portal/home"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        FEMA MSC / NFHL
                      </a>{' '}
                      — flood zone at the pin
                    </li>
                    <li>Municipal code / noise ordinance pages for the city (often Unverified until citeable)</li>
                  </ul>
                </div>
                {(view.environmental_screening?.findings || []).slice(0, findingsVisible).map((finding, idx) => {
                  const risk = String(finding.risk_level || '').toUpperCase();
                  const verified = Boolean(finding.verified);
                  const pinMissing = !hasUsableCoords(view);
                  // Only claim "NOT RUN" when the pin is missing. PRELIMINARY/UNKNOWN with a pin
                  // means the layer ran but is not parcel-GIS verified — show the real description.
                  const notRun =
                    pinMissing && (risk === 'PRELIMINARY' || risk === 'UNKNOWN' || incompleteRun);
                  const unverified =
                    !notRun && !verified && (risk === 'PRELIMINARY' || risk === 'UNKNOWN');
                  return (
                  <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2 gap-2">
                      <h4 className="font-bold text-white capitalize">
                        {finding.category.replace(/_/g, ' ')}
                      </h4>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-semibold ${
                          notRun || unverified
                            ? 'bg-amber-500/20 text-amber-200'
                            : getRiskColor(finding.risk_level)
                        }`}
                      >
                        {notRun
                          ? 'NOT RUN — confirm pin'
                          : unverified
                            ? `${finding.risk_level || 'UNKNOWN'} — not GIS-verified`
                            : finding.risk_level}
                      </span>
                    </div>
                    <p className="text-gray-300 text-sm mb-2">
                      {notRun
                        ? 'Parcel GIS / environmental layers did not complete for this run. Confirm the map pin and re-check to replace this placeholder.'
                        : finding.description}
                    </p>
                    {!notRun && (finding.action_items || []).length > 0 && (
                      <ul className="space-y-1 mb-2">
                        {finding.action_items.slice(0, 3).map((item, i) => (
                          <li key={i} className="text-xs text-gray-400 flex gap-2">
                            <span className="text-purple-400">•</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {!notRun && (
                    <CitationBadge
                      data_sources={finding.data_sources}
                      source_url={finding.source_url}
                      source_label={finding.source_label || (finding.data_sources || [])[0]}
                      verified={verified}
                      citation_tier={
                        verified ? 'source' : finding.source_url ? 'link' : 'unverified'
                      }
                    />
                    )}
                  </div>
                  );
                })}
                {softLocked &&
                  (view.environmental_screening?.findings || []).length > findingsVisible && (
                    <div className="space-y-2">
                      {(view.environmental_screening?.findings || [])
                        .slice(findingsVisible, findingsVisible + 2)
                        .map((finding, idx) => (
                          <div
                            key={`blur-find-${idx}`}
                            className="relative overflow-hidden rounded-lg border border-purple-500/30 bg-slate-800/40 p-4 select-none"
                            aria-hidden
                          >
                            <div className="blur-sm opacity-70 pointer-events-none">
                              <h4 className="font-bold text-white capitalize">
                                {String(finding.category || 'layer').replace(/_/g, ' ')}
                              </h4>
                              <p className="text-gray-300 text-sm mt-1">{finding.description}</p>
                            </div>
                            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/55">
                              <span className="text-[11px] font-bold uppercase tracking-wide text-purple-100 px-2 py-1 rounded bg-purple-600/40 border border-purple-400/40">
                                Locked
                              </span>
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
