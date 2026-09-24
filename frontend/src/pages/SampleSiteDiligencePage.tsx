/**
 * Sample of the on-screen results panel after address entry.
 * ?tier=free|partner|pro shows progressive unlock + blur ladder.
 */

import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Loader2 } from 'lucide-react';
import ResultsViewerModal, { type AnalysisData } from '../components/ResultsViewerModal';
import { ErrorBoundary } from '../components/ErrorBoundary';
import {
  analysisForSampleDemo,
  parseSampleDemoTier,
  sampleDemoLabel,
} from '../sampleDemoTier';
import { PRODUCT_COPY } from '../productCopy';

export default function SampleSiteDiligencePage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const demoTier = parseSampleDemoTier(params.get('tier'));
  const [base, setBase] = useState<AnalysisData | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void fetch('/sample/site-diligence-analysis.json', { credentials: 'omit' })
      .then(async (res) => {
        if (!res.ok) throw new Error(`Sample analysis missing (${res.status})`);
        return res.json() as Promise<AnalysisData>;
      })
      .then((data) => {
        if (cancelled) return;
        setBase(data);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Could not load sample analysis');
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const analysis = useMemo(
    () => (base ? analysisForSampleDemo(base, demoTier) : null),
    [base, demoTier]
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-900 to-[#0a1429] flex items-center justify-center text-white">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-900 to-[#0a1429] flex items-center justify-center px-4 text-white">
        <div className="max-w-md text-center">
          <AlertCircle className="w-8 h-8 text-amber-300 mx-auto mb-3" />
          <p className="font-bold mb-2">Sample results unavailable</p>
          <p className="text-sm text-gray-300 mb-4">{error || 'Missing sample analysis'}</p>
          <Link to="/" className="text-emerald-300 font-semibold underline">
            Back to home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-900 to-[#0a1429] px-3 py-4 sm:px-6 sm:py-6">
      <div className="max-w-5xl mx-auto mb-4 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => navigate('/#sample-report')}
          className="inline-flex items-center gap-2 text-emerald-300 hover:text-white font-semibold min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to samples
        </button>
        <a
          href="#rg-executive-summary"
          className="inline-flex items-center px-3 py-2 rounded-lg border border-amber-400/50 bg-amber-500/15 text-amber-100 text-sm font-bold min-h-[44px]"
        >
          Jump to Executive Summary
        </a>
      </div>
      <p className="max-w-5xl mx-auto mb-2 text-xs font-bold tracking-wide text-amber-300">
        {PRODUCT_COPY.sampleEyebrow} — same panel you get after entering an address
      </p>
      {demoTier ? (
        <p className="max-w-5xl mx-auto mb-3 text-sm font-semibold text-emerald-200">
          {sampleDemoLabel(demoTier)}
        </p>
      ) : null}
      <div className="max-w-5xl mx-auto">
        <ErrorBoundary>
          <ResultsViewerModal
            isOpen
            onClose={() => navigate('/#sample-report')}
            analysis={analysis}
            researchId={analysis.research_id || 'rg-sample-chapin-fw'}
            demoTier={demoTier}
          />
        </ErrorBoundary>
      </div>
    </div>
  );
}
