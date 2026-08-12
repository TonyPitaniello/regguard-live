/**
 * RegGuard Sample Report — Real anonymized example
 * Shows buyers exactly what they'll get
 */

import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, Download } from 'lucide-react';
import { backendUrl } from '../env';

export default function SampleReportPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Back Button */}
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center">
          <button onClick={() => navigate('/')} className="flex items-center gap-2 text-purple-400 hover:text-purple-300 transition">
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl font-black text-white mb-6">Sample Report</h1>
          <p className="text-xl text-gray-300 mb-6">
            Here's a real anonymized RegGuard report. This is exactly what you'll receive when you order.
          </p>
          <a
            href={backendUrl('/sample/plano-punch-list.pdf')}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition min-h-[44px]"
          >
            <Download className="w-4 h-4" />
            Download SAMPLE Plano punch list (PDF)
          </a>
          <p className="text-gray-500 text-sm mt-3">
            Labeled SAMPLE — fictional Plano address for buyers. Not a live diligence deliverable.
          </p>
        </div>
      </section>

      {/* Sample Report Content */}
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-purple-500/30 rounded-xl p-12 text-gray-300 space-y-8">
          
          {/* Header */}
          <div className="border-b border-purple-500/20 pb-8">
            <h2 className="text-3xl font-black text-white mb-4">DATA CENTER SITE DILIGENCE REPORT</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Site</p>
                <p className="text-white font-bold">Large Industrial Parcel (250 MW Capacity)</p>
              </div>
              <div>
                <p className="text-gray-500">Location</p>
                <p className="text-white font-bold">Texas (Anonymized)</p>
              </div>
              <div>
                <p className="text-gray-500">RTO</p>
                <p className="text-white font-bold">ERCOT</p>
              </div>
              <div>
                <p className="text-gray-500">Report Date</p>
                <p className="text-white font-bold">June 28, 2026</p>
              </div>
            </div>
          </div>

          {/* Executive Summary */}
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Executive Summary</h3>
            <div className="space-y-4">
              <div className="flex gap-4">
                <CheckCircle className="w-6 h-6 text-green-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-white font-bold">Recommendation: GO</p>
                  <p className="text-gray-400">Interconnection viable via standard large-load path (12–18 months Phase 1 feasibility study)</p>
                </div>
              </div>
              <div className="mt-6 bg-slate-700/50 rounded-lg p-4">
                <p className="text-white font-bold mb-3">Key Findings:</p>
                <ul className="space-y-2 text-sm">
                  <li>✓ Site within ERCOT transmission area; large-load interconnection path available</li>
                  <li>✓ No state-level moratorium; Texas has no statewide data center restrictions</li>
                  <li>✓ Preliminary network upgrade cost estimate: $15M–$40M (to be refined in Phase 1)</li>
                  <li>✓ No critical environmental blockers identified</li>
                  <li>✓ Interconnection timeline: 12–18 months Phase 1 + 12–18 months Phase 2/3 if upgrades needed</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Interconnection Process */}
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Interconnection Process Timeline</h3>
            <div className="space-y-3 text-sm">
              <div className="flex gap-4">
                <span className="text-purple-400 font-bold min-w-fit">Phase 1 (12–18 mo):</span>
                <span>Feasibility study — ERCOT determines system capacity at your POI</span>
              </div>
              <div className="flex gap-4">
                <span className="text-purple-400 font-bold min-w-fit">Phase 2 (12–18 mo):</span>
                <span>System impact study — Network upgrade requirements defined</span>
              </div>
              <div className="flex gap-4">
                <span className="text-purple-400 font-bold min-w-fit">Phase 3 (6–12 mo):</span>
                <span>Facilities study — Final design and interconnection agreement</span>
              </div>
              <div className="flex gap-4">
                <span className="text-purple-400 font-bold min-w-fit">Total: 30–48+ months</span>
                <span>From application to grid connection</span>
              </div>
            </div>
          </div>

          {/* Regulatory Landscape */}
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Regulatory Landscape</h3>
            <div className="space-y-4">
              <div>
                <p className="text-white font-bold text-sm">Federal (FERC)</p>
                <p className="text-gray-400 text-sm">FERC Order 2023 applies. Large power plants (250+ MW) require compliance. Standard rules for utility-scale interconnection.</p>
              </div>
              <div>
                <p className="text-white font-bold text-sm">State (Texas)</p>
                <p className="text-gray-400 text-sm">No data center moratoria. Pro-development environment. Texas PUC monitors utility compliance.</p>
              </div>
              <div>
                <p className="text-white font-bold text-sm">Local</p>
                <p className="text-gray-400 text-sm">Industrial zoning typically allows large projects. Conditional use permit (CUP) may be required but standard for this parcel type.</p>
              </div>
            </div>
          </div>

          {/* Preliminary Costs */}
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Preliminary Cost Estimate</h3>
            <div className="bg-slate-700/50 rounded-lg p-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span>Network upgrades (estimate):</span>
                <span className="text-white font-bold">$15M–$40M</span>
              </div>
              <div className="flex justify-between">
                <span>Utility customer contribution:</span>
                <span className="text-white font-bold">$2M–$5M</span>
              </div>
              <div className="flex justify-between">
                <span>Study costs (Phase 1–3):</span>
                <span className="text-white font-bold">$100K–$500K</span>
              </div>
              <p className="text-gray-400 text-xs pt-4 border-t border-slate-600">
                Note: Estimates based on historical data for your MW range and RTO. Actual costs determined during Phase 1 study. This is preliminary only.
              </p>
            </div>
          </div>

          {/* Risk Assessment */}
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Risk Assessment</h3>
            <div className="space-y-3 text-sm">
              <div className="flex gap-3">
                <span className="text-yellow-400 font-bold">⚠</span>
                <div>
                  <p className="text-white font-bold">Transmission Constraints (Medium Risk)</p>
                  <p className="text-gray-400">This transmission node has experienced congestion in summer 2025. Phase 1 study will clarify upgrade requirements.</p>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="text-yellow-400 font-bold">⚠</span>
                <div>
                  <p className="text-white font-bold">Timeline Sensitivity (Medium Risk)</p>
                  <p className="text-gray-400">ERCOT queue depth is 18–24 months for large load. Utility study delays are common.</p>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="text-green-400 font-bold">✓</span>
                <div>
                  <p className="text-white font-bold">Permitting Risk (Low)</p>
                  <p className="text-gray-400">Texas regulatory environment is pro-development. No anticipated local opposition.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Next Steps */}
          <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-6">
            <h3 className="text-lg font-bold text-white mb-4">Recommended Next Steps</h3>
            <ol className="space-y-3 text-sm">
              <li><span className="text-blue-400 font-bold">1.</span> <span className="text-white">Schedule pre-application meeting with utility interconnection team</span></li>
              <li><span className="text-blue-400 font-bold">2.</span> <span className="text-white">Engage IC consultant to guide Phase 1 scope and cost negotiation</span></li>
              <li><span className="text-blue-400 font-bold">3.</span> <span className="text-white">Submit formal interconnection application to ERCOT (with IC consultant support)</span></li>
              <li><span className="text-blue-400 font-bold">4.</span> <span className="text-white">Retain environmental counsel for any required reviews</span></li>
            </ol>
          </div>

          {/* Disclaimer */}
          <div className="border-t border-purple-500/20 pt-8">
            <p className="text-xs text-gray-500">
              <strong>DISCLAIMER:</strong> This is a sample anonymized report showing the structure, depth, and quality of RegGuard analysis. Actual reports are customized to your specific site, jurisdiction, and project type. All findings are based on public sources and cited for independent verification. This report is not legal advice, engineering advice, or a guarantee of interconnection approval.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10 bg-slate-900/50">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-black text-white mb-6">Ready to see this for your site?</h2>
          <p className="text-gray-300 mb-8">Try free (memo only) or order the full package with punch list and permit forms.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => navigate('/free-trial')}
              className="px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold rounded-lg transition cursor-pointer"
            >
              Try Free
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-8 py-3 border border-purple-500/50 hover:border-purple-500 text-white font-bold rounded-lg transition bg-slate-900/50 hover:bg-slate-900 cursor-pointer"
            >
              Back to Home
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
