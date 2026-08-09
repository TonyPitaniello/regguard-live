/**
 * Client-side instant analysis when production API returns no analysis_data
 * (e.g. stale Render deploy). Keeps ResultsViewerModal opening every time.
 * Honesty layer: never emit stub LOW/MEDIUM/HIGH as overall risk truth.
 */

import type { AnalysisData } from './ResultsViewerModal';

export function buildClientInstantAnalysis(input: {
  address: string;
  city: string;
  state: string;
  zip: string;
  projectType: string;
}): AnalysisData {
  const { address, city, state, zip, projectType } = input;
  const findings = [
    {
      category: 'electrical_interconnection',
      risk_level: 'PRELIMINARY',
      description: `Preliminary scan for ${city}, ${state} ${zip}: confirm utility interconnection and AHJ electrical permit path for ${projectType}.`,
      action_items: [
        'Identify serving utility and interconnection portal',
        'Confirm local electrical code amendments',
        'Request preliminary study timeline from utility',
      ],
      data_sources: ['RegGuard Instant Preview'],
      research_cost_usd: 0,
    },
    {
      category: 'permitting',
      risk_level: 'PRELIMINARY',
      description: `Local permitting for ${projectType} typically needs building/electrical permits plus utility coordination.`,
      action_items: [
        'Call AHJ planning desk with this address',
        'Confirm required permit package documents',
        'Check floodplain / environmental overlays',
      ],
      data_sources: ['RegGuard Instant Preview'],
      research_cost_usd: 0,
    },
    {
      category: 'timeline_cost',
      risk_level: 'PRELIMINARY',
      description: 'Instant preview estimate. Full diligence may refine timeline and cost. Figures are unverified.',
      action_items: [
        'Budget 30–180 days depending on utility track',
        'Confirm every fee with the AHJ before bidding',
      ],
      data_sources: ['RegGuard Instant Preview'],
      research_cost_usd: 0,
    },
  ];

  const punchList = [
    {
      priority: 'HIGH',
      task: `Confirm AHJ contact for ${city}, ${state}`,
      responsible_party: 'Project owner / permitting lead',
      timeline: 'Week 1',
      estimated_cost: 500,
      notes: 'Instant preview — unverified estimate',
      verified: false,
      cost_verified: false,
      source_label: 'Instant preview',
    },
    {
      priority: 'HIGH',
      task: 'Identify utility interconnection application',
      responsible_party: 'Electrical / IC consultant',
      timeline: 'Week 1–2',
      estimated_cost: 1500,
      cost_verified: false,
      notes: `Project type: ${projectType}`,
      verified: false,
      cost_verified: false,
      source_label: 'Instant preview',
    },
    {
      priority: 'MEDIUM',
      task: 'Assemble site plan and one-line diagram',
      responsible_party: 'Design engineer',
      timeline: 'Week 2–4',
      estimated_cost: 5000,
      cost_verified: false,
      notes: '',
      verified: false,
      cost_verified: false,
      source_label: 'Instant preview',
    },
  ];

  const totalCost = punchList.reduce((s, i) => s + (i.estimated_cost || 0), 0);

  return {
    timestamp: new Date().toISOString(),
    preview: true,
    honesty: {
      risk_verified: false,
      cost_verified: false,
      timeline_verified: false,
      source: 'client',
      labels: {
        risk: 'Environmental risk score unavailable — not verified against parcel GIS data. Do not use for bidding.',
        cost: 'Unverified estimate — not an AHJ fee quote. Confirm with the local AHJ.',
        timeline: 'Unverified estimate — confirm with AHJ / utility study track.',
      },
    },
    project_info: {
      address,
      city,
      state,
      zip,
      type: projectType,
      coordinates: { latitude: 0, longitude: 0 },
    },
    environmental_screening: {
      risk_level: 'UNAVAILABLE',
      risk_score_hidden: true,
      findings,
      total_research_cost: 0,
      action_plan: findings.flatMap((f) => f.action_items.slice(0, 1)),
    },
    punch_list: {
      punch_list: punchList,
      timeline_summary: '30–120 days (instant estimate)',
      estimated_total_cost: totalCost,
      estimates_unverified: true,
      critical_path: punchList
        .filter((i) => i.priority === 'HIGH')
        .map((i) => ({
          task: i.task,
          verified: false,
          cost_verified: false,
          source_label: 'Instant preview',
          estimated_cost: i.estimated_cost,
        })),
      estimates_verified: false,
      milestones: [
        { week: '1', milestone: 'AHJ + utility contacts confirmed' },
        { week: '4', milestone: 'Application package drafted' },
      ],
      who_to_call: {
        AHJ: `${city} building/permitting department`,
        Utility: 'Serving electric utility interconnection desk',
      },
    },
    summary: {
      total_environmental_risks: findings.length,
      high_risk_count: 0,
      total_punch_list_items: punchList.length,
      estimated_timeline: '30–120 days (instant estimate) (unverified)',
      estimated_total_cost: totalCost,
      estimates_unverified: true,
      cost_verified: false,
      timeline_verified: false,
      risk_verified: false,
    },
    next_steps: [
      'Treat this as a preview checklist — risk scores are not parcel-verified',
      'Confirm every dollar and day estimate with the AHJ before bidding',
      'Upgrade to Contractor Pro for citeable research memos with source URLs',
    ],
  };
}
