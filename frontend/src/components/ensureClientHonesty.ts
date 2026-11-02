/**
 * Normalize any free-trial analysis payload so stub risk never displays as truth,
 * even if a stale API returns MEDIUM without honesty metadata.
 */

import type { AnalysisData } from './ResultsViewerModal';
import type { HonestyMeta } from './honesty';
import { isRiskScoreHidden } from './honesty';

const DEFAULT_LABELS: NonNullable<HonestyMeta['labels']> = {
  risk: 'Flood and wetlands stay Unverified until a FEMA or NWI page is attached. This is not a 0–100 score.',
  cost: 'No permit total. When the city uses a valuation or floor-area table, confirm that table with the AHJ.',
  timeline: 'Timeline is Unverified. Confirm with the AHJ. This is not a filing date.',
};

export function ensureClientHonesty(analysis: AnalysisData): AnalysisData {
  const existing = analysis.honesty;
  const riskVerified = existing?.risk_verified === true;
  const costVerified = existing?.cost_verified === true;
  const timelineVerified = existing?.timeline_verified === true;

  // Already honest and verified — pass through
  if (riskVerified && costVerified && timelineVerified) {
    return analysis;
  }

  const level = (analysis.environmental_screening?.risk_level || '').toUpperCase();
  const needsRiskHide =
    !riskVerified &&
    (analysis.preview ||
      analysis.environmental_screening?.risk_score_hidden ||
      ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'UNAVAILABLE', 'PRELIMINARY', ''].includes(level));

  if (!needsRiskHide && existing && !analysis.preview) {
    // Non-preview without hide need — still ensure estimates flags if missing
    if (analysis.summary?.estimates_unverified) return analysis;
  }

  const findings = (analysis.environmental_screening?.findings || []).map((f) => {
    const rl = (f.risk_level || '').toUpperCase();
    if (!riskVerified && ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(rl)) {
      return { ...f, risk_level: 'PRELIMINARY' };
    }
    return f;
  });

  let timeline = analysis.summary?.estimated_timeline || '';
  if (!timelineVerified && timeline && !timeline.toLowerCase().includes('unverified')) {
    timeline = `${timeline} (unverified)`;
  }

  return {
    ...analysis,
    preview: analysis.preview ?? true,
    honesty: {
      risk_verified: false,
      cost_verified: costVerified,
      timeline_verified: timelineVerified,
      source: existing?.source || 'client_normalize',
      labels: { ...DEFAULT_LABELS, ...(existing?.labels || {}) },
    },
    environmental_screening: {
      ...analysis.environmental_screening,
      risk_level: riskVerified ? analysis.environmental_screening.risk_level : 'UNAVAILABLE',
      risk_score_hidden: !riskVerified,
      findings,
    },
    punch_list: {
      ...analysis.punch_list,
      estimates_unverified: !costVerified,
      punch_list: (analysis.punch_list?.punch_list || []).map((item) => ({
        ...item,
        cost_verified: item.cost_verified ?? false,
        estimates_unverified: true,
      })),
    },
    summary: {
      ...analysis.summary,
      high_risk_count: riskVerified ? analysis.summary.high_risk_count : 0,
      estimated_timeline: timeline,
      estimates_unverified: !costVerified || !timelineVerified,
      cost_verified: costVerified,
      timeline_verified: timelineVerified,
      risk_verified: false,
    },
  };
}

/** Test helper — mirrors isRiskScoreHidden for normalize output */
export function clientRiskIsHidden(analysis: AnalysisData): boolean {
  return isRiskScoreHidden(ensureClientHonesty(analysis));
}
