/**
 * Sample Report — same Fort Worth DC-adjacent site at every paid tier.
 * Downloads use production generators labeled SAMPLE.
 */

import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { SampleReportBlock } from '../components/SampleReportBlock';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';

export default function SampleReportPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between gap-4">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <button
            type="button"
            onClick={() => navigate('/pricing')}
            className="text-sm font-semibold text-emerald-300 hover:text-white transition"
          >
            Pricing
          </button>
        </div>
      </header>

      <section className="px-4 py-14 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <SampleReportBlock />

          <div className="mt-10 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5">
            <p className="text-emerald-100 font-bold mb-2">{IC_BUNDLE.productName} ZIP contains</p>
            <ul className="space-y-1.5 text-sm text-gray-300">
              {IC_BUNDLE.contents.map((c) => (
                <li key={c.file}>
                  <span className="text-white font-semibold">{c.label}</span>
                  <span className="text-gray-500"> · {c.file}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
