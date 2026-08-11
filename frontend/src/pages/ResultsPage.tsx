/**
 * ResultsPage.tsx
 * Full-page fallback for analysis results (same share options as modal overlay).
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Download, ChevronDown, ChevronUp } from 'lucide-react';
import SendResultsForm from '../components/SendResultsForm';
import CitationBadge from '../components/CitationBadge';
import { buildSummaryFromAnalysis, AnalysisData, CriticalPathItem } from '../components/ResultsViewerModal';

function criticalPathTask(item: CriticalPathItem): string {
  return typeof item === 'string' ? item : item.task;
}

export default function ResultsPage() {
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [researchId, setResearchId] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    environmental: true,
    punchList: true,
    critical: true,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const defaultEmail = typeof window !== 'undefined' ? sessionStorage.getItem('userEmail') || '' : '';

  useEffect(() => {
    const stored = sessionStorage.getItem('analysisResults');
    const storedId = sessionStorage.getItem('researchId');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setAnalysis(parsed);
        setResearchId(storedId || parsed.research_id || null);
        setLoading(false);
      } catch {
        setError('Failed to load results');
        setLoading(false);
      }
    } else {
      setError('No analysis results found. Please run the free trial first.');
      setLoading(false);
    }
  }, []);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const getRiskColor = (level: string) => {
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
  };

  const getPriorityBadge = (priority: string) => {
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
  };

  const downloadResults = () => {
    if (!analysis) return;
    const dataStr = JSON.stringify(analysis, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `regguard-analysis-${analysis.project_info.zip}.json`;
    link.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4" />
          <p className="text-gray-300">Loading your analysis...</p>
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6 max-w-md">
          <AlertCircle className="w-6 h-6 text-red-500 mb-4" />
          <p className="text-red-200">{error || 'Failed to load analysis'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="max-w-6xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="mb-12">
          <h1 className="text-4xl font-black text-white mb-2">Your Site Diligence Analysis</h1>
          <p className="text-gray-400">
            {analysis.project_info.address} • {analysis.project_info.city}, {analysis.project_info.state}{' '}
            {analysis.project_info.zip}
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Analysis completed: {new Date(analysis.timestamp).toLocaleDateString()}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-gradient-to-br from-blue-600/20 to-blue-900/20 border border-blue-500/30 rounded-lg p-6">
            <div className="text-3xl font-black text-blue-400 mb-2">
              {analysis.summary.total_environmental_risks}
            </div>
            <p className="text-gray-300">Environmental Issues Found</p>
          </div>
          <div className="bg-gradient-to-br from-orange-600/20 to-orange-900/20 border border-orange-500/30 rounded-lg p-6">
            <div className="text-3xl font-black text-orange-400 mb-2">
              {analysis.summary.high_risk_count}
            </div>
            <p className="text-gray-300">High/Critical Risks</p>
          </div>
          <div
            className={`bg-gradient-to-br ${
              analysis.environmental_screening.risk_level === 'LOW'
                ? 'from-green-600/20 to-green-900/20 border-green-500/30'
                : analysis.environmental_screening.risk_level === 'MEDIUM'
                  ? 'from-yellow-600/20 to-yellow-900/20 border-yellow-500/30'
                  : 'from-red-600/20 to-red-900/20 border-red-500/30'
            } border rounded-lg p-6`}
          >
            <div
              className={`text-2xl font-black mb-2 ${
                analysis.environmental_screening.risk_level === 'LOW'
                  ? 'text-green-400'
                  : analysis.environmental_screening.risk_level === 'MEDIUM'
                    ? 'text-yellow-400'
                    : 'text-red-400'
              }`}
            >
              {analysis.environmental_screening.risk_level} Risk
            </div>
            <p className="text-gray-300">Overall Assessment</p>
          </div>
        </div>

        <section className="mb-8">
          <button
            onClick={() => toggleSection('environmental')}
            className="w-full flex items-center justify-between bg-gradient-to-r from-purple-600/20 to-blue-600/20 border border-purple-500/30 rounded-lg p-6 mb-4 hover:border-purple-500/50 transition"
          >
            <h2 className="text-2xl font-bold text-white">Environmental Findings</h2>
            {expandedSections.environmental ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {expandedSections.environmental && (
            <div className="space-y-4">
              {analysis.environmental_screening.findings.map((finding, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-lg font-bold text-white capitalize">
                      {finding.category.replace(/_/g, ' ')}
                    </h3>
                    <span
                      className={`px-3 py-1 rounded text-sm font-semibold ${getRiskColor(finding.risk_level)}`}
                    >
                      {finding.risk_level}
                    </span>
                  </div>
                  <p className="text-gray-300 mb-4">{finding.description}</p>
                  <div className="mb-4">
                    <p className="text-sm font-semibold text-gray-400 mb-2">Action Items:</p>
                    <ul className="space-y-2">
                      {finding.action_items.map((item, i) => (
                        <li key={i} className="text-sm text-gray-300 flex items-start">
                          <span className="mr-3 text-purple-400">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
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

        <section className="mb-8">
          <button
            onClick={() => toggleSection('critical')}
            className="w-full flex items-center justify-between bg-gradient-to-r from-red-600/20 to-orange-600/20 border border-red-500/30 rounded-lg p-6 mb-4 hover:border-red-500/50 transition"
          >
            <h2 className="text-2xl font-bold text-white">Pre-bid punch list (critical)</h2>
            {expandedSections.critical ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {expandedSections.critical && (
            <div className="space-y-3">
              <p className="text-xs text-gray-400 px-1">
                Every line shows a source link or <span className="text-amber-300 font-semibold">Unverified</span>.
              </p>
              {analysis.punch_list.critical_path.map((task, idx) => {
                const meta = typeof task === 'string' ? { task } : task;
                return (
                  <div key={idx} className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
                    <div className="flex items-start">
                      <span className="text-red-400 font-bold mr-3">{idx + 1}.</span>
                      <div className="flex-1">
                        <p className="text-gray-200">{criticalPathTask(task)}</p>
                        <CitationBadge
                          source_url={meta.source_url}
                          source_label={meta.source_label}
                          verified={meta.verified}
                          cost_verified={meta.cost_verified}
                          estimated_cost={meta.estimated_cost}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section className="mb-8">
          <button
            onClick={() => toggleSection('punchList')}
            className="w-full flex items-center justify-between bg-gradient-to-r from-green-600/20 to-emerald-600/20 border border-green-500/30 rounded-lg p-6 mb-4 hover:border-green-500/50 transition"
          >
            <div>
              <h2 className="text-2xl font-bold text-white">Full Action Plan</h2>
              <p className="text-sm text-gray-400 mt-1">
                {analysis.summary.total_punch_list_items} items • Est. {analysis.summary.estimated_timeline}
              </p>
            </div>
            {expandedSections.punchList ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {expandedSections.punchList && (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {analysis.punch_list.punch_list.slice(0, 20).map((item, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <p className="text-white font-semibold flex-1">{item.task}</p>
                    <span
                      className={`px-2 py-1 rounded text-xs font-semibold whitespace-nowrap ml-2 ${getPriorityBadge(item.priority)}`}
                    >
                      {item.priority}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                    <span>📅 {item.timeline}</span>
                    <span>👤 {item.responsible_party}</span>
                    {item.estimated_cost ? (
                      <span>💰 ${item.estimated_cost.toLocaleString()}</span>
                    ) : null}
                  </div>
                  <CitationBadge
                    source_url={item.source_url}
                    source_label={item.source_label}
                    verified={item.verified}
                    cost_verified={item.cost_verified}
                    estimated_cost={item.estimated_cost}
                  />
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-lg p-6">
            <h3 className="text-lg font-bold text-white mb-4">Timeline</h3>
            <p className="text-2xl font-black text-blue-400">{analysis.summary.estimated_timeline}</p>
            <CitationBadge verified={false} source_label="Estimate — confirm with AHJ" />
          </div>
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-lg p-6">
            <h3 className="text-lg font-bold text-white mb-4">Estimated Cost</h3>
            <p className="text-2xl font-black text-green-400">
              ${analysis.summary.estimated_total_cost.toLocaleString()}
            </p>
            <CitationBadge
              verified={Boolean(analysis.punch_list?.estimates_verified)}
              cost_verified={Boolean(analysis.punch_list?.estimates_verified)}
              estimated_cost={analysis.summary.estimated_total_cost}
              source_label="Rollup of line items"
            />
          </div>
        </div>

        {/* Upgrade CTA — multi-segment */}
        <div className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 border border-purple-500/30 rounded-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-white mb-4">Ready for more?</h2>
          <p className="text-gray-300 mb-6">
            This free lookup gives you key findings. Upgrade for full packages:
          </p>
          <div className="grid sm:grid-cols-2 gap-4 mb-6">
            <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4">
              <p className="text-white font-bold">Contractor Pro</p>
              <p className="text-emerald-400 font-black text-xl">$149/mo</p>
              <p className="text-gray-400 text-sm mt-1">Unlimited lookups + punch lists</p>
            </div>
            <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4">
              <p className="text-white font-bold">IC Project Report</p>
              <p className="text-emerald-400 font-black text-xl">$1,500</p>
              <p className="text-gray-400 text-sm mt-1">One-time full project deliverable</p>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => {
                const email = (sessionStorage.getItem('userEmail') || '').trim().toLowerCase();
                sessionStorage.setItem('pendingDeepUnlock', '1');
                navigate(
                  `/checkout/contractor_pro${email ? `?email=${encodeURIComponent(email)}` : ''}`
                );
              }}
              className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white font-bold py-3 px-6 rounded-lg transition"
            >
              Get Contractor Pro — $149/mo
            </button>
            <button
              onClick={() => {
                const email = (sessionStorage.getItem('userEmail') || '').trim().toLowerCase();
                sessionStorage.setItem('pendingDeepUnlock', '1');
                navigate(
                  `/checkout/ic_project${email ? `?email=${encodeURIComponent(email)}` : ''}`
                );
              }}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold py-3 px-6 rounded-lg transition"
            >
              Order IC Report — $1,500
            </button>
            <button
              onClick={() => navigate('/pricing')}
              className="border border-slate-600 text-gray-200 font-semibold py-3 px-6 rounded-lg hover:bg-slate-800 transition"
            >
              See all pricing
            </button>
          </div>
        </div>

        {/* Dual text + email send */}
        <section className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6 mb-8">
          <SendResultsForm
            researchId={researchId}
            summary={buildSummaryFromAnalysis(analysis)}
            defaultEmail={defaultEmail}
          />
        </section>

        <div className="flex gap-4 justify-center">
          <button
            onClick={downloadResults}
            className="bg-slate-800 hover:bg-slate-700 text-white font-semibold py-2 px-6 rounded-lg border border-slate-700 hover:border-slate-600 transition flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download JSON
          </button>
          <button
            onClick={() => window.print()}
            className="bg-slate-800 hover:bg-slate-700 text-white font-semibold py-2 px-6 rounded-lg border border-slate-700 hover:border-slate-600 transition"
          >
            Print Results
          </button>
        </div>
      </div>
    </div>
  );
}
