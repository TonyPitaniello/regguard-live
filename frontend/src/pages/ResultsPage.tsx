/**
 * ResultsPage — /results fallback uses the same ResultsViewerModal as home.
 */

import { useEffect, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import ResultsViewerModal, { AnalysisData } from '../components/ResultsViewerModal';
import { ErrorBoundary } from '../components/ErrorBoundary';

export default function ResultsPage() {
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [researchId, setResearchId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const defaultEmail =
    typeof window !== 'undefined' ? sessionStorage.getItem('userEmail') || '' : '';

  useEffect(() => {
    const stored = sessionStorage.getItem('analysisResults');
    const storedId = sessionStorage.getItem('researchId');
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as AnalysisData;
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-3 py-6 sm:px-6">
      <div className="max-w-5xl mx-auto">
        <ErrorBoundary>
          <ResultsViewerModal
            isOpen
            onClose={() => {
              window.location.assign('/?resume=1');
            }}
            analysis={analysis}
            researchId={researchId}
            defaultEmail={defaultEmail}
          />
        </ErrorBoundary>
      </div>
    </div>
  );
}
