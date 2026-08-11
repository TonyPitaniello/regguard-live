/**
 * Shared free-trial form used on homepage (/) and /free-trial
 * Always opens ResultsViewerModal — even if API returns no analysis_data.
 * Listens for voice-fill events from VoiceCommandSystem.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, Loader2, MapPin, Search, ListChecks } from 'lucide-react';
import { LocationPicker } from './LocationPicker';
import { backendUrl } from '../env';
import ResultsViewerModal, { AnalysisData } from './ResultsViewerModal';
import { buildClientInstantAnalysis } from './buildClientInstantAnalysis';
import { ensureClientHonesty } from './ensureClientHonesty';
import {
  VOICE_FILL_EVENT,
  VOICE_SUBMIT_EVENT,
  type VoiceFillDetail,
} from '../voiceFillParse';
import { getOwnerKey, setJobsEmail } from '../jobsOwner';

function generateClientResearchId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `ft-${crypto.randomUUID()}`;
  }
  return `ft-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

type ProgressStep = 'geocode' | 'screen' | 'punch';

const PROGRESS_LABELS: Record<ProgressStep, string> = {
  geocode: 'Geocoding site…',
  screen: 'Screening permits & environment…',
  punch: 'Building punch list…',
};

function initialEmailFromStorage(): string {
  if (typeof window === 'undefined') return '';
  const params = new URLSearchParams(window.location.search);
  const fromQuery = (params.get('email') || '').trim().toLowerCase();
  if (fromQuery) return fromQuery;
  return (sessionStorage.getItem('userEmail') || '').trim().toLowerCase();
}

export default function FreeTrialForm({ showHero = false }: { showHero?: boolean }) {
  const [formData, setFormData] = useState({
    address: '',
    city: '',
    state: '',
    zip: '',
    projectType: 'data-center',
    email: initialEmailFromStorage(),
    phone: '',
  });
  const [externalLocation, setExternalLocation] = useState<{
    address?: string;
    city?: string;
    state?: string;
    zip?: string;
  } | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState<ProgressStep>('geocode');
  const [resultsOpen, setResultsOpen] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [researchId, setResearchId] = useState<string | null>(null);
  const [voiceHint, setVoiceHint] = useState('');
  const formDataRef = useRef(formData);
  formDataRef.current = formData;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleLocationSelect = (
    address: string,
    city: string,
    state: string,
    zip: string,
    _lat: number,
    _lng: number
  ) => {
    setFormData((prev) => ({
      ...prev,
      address,
      city,
      state,
      zip,
    }));
  };

  const showResults = useCallback((analysisPayload: AnalysisData, id: string, email?: string) => {
    const honest = ensureClientHonesty({ ...analysisPayload, research_id: id });
    sessionStorage.setItem('analysisResults', JSON.stringify(honest));
    sessionStorage.setItem('researchId', id);
    const mail = email || formDataRef.current.email;
    if (mail) {
      sessionStorage.setItem('userEmail', mail);
      setJobsEmail(mail);
    }
    setResearchId(id);
    setAnalysis(honest);
    setResultsOpen(true);

    // Persist for shareable /r/{id} — non-blocking
    void fetch(backendUrl('/research/persist'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis: honest, research_id: id }),
    })
      .then(async (res) => {
        if (!res.ok) return;
        const meta = await res.json();
        if (meta?.share_url && meta?.research_id) {
          const withShare = {
            ...honest,
            research_id: meta.research_id as string,
            share_url: meta.share_url as string,
          };
          sessionStorage.setItem('analysisResults', JSON.stringify(withShare));
          sessionStorage.setItem('researchId', meta.research_id);
          setResearchId(meta.research_id);
          setAnalysis(withShare as AnalysisData);

          // Upsert Saved Job (client) so /jobs works even if server auto-save missed
          if (mail) {
            const p = withShare.project_info;
            void fetch(backendUrl('/jobs'), {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                owner_email: mail,
                owner_key: getOwnerKey(),
                address: p.address,
                city: p.city,
                state: p.state,
                zip: p.zip,
                project_type: p.type || formDataRef.current.projectType,
                last_research_id: meta.research_id,
                share_url: meta.share_url,
                summary_snapshot: {
                  estimated_timeline: withShare.summary?.estimated_timeline,
                  estimated_total_cost: withShare.summary?.estimated_total_cost,
                  risk_level: withShare.environmental_screening?.risk_level,
                  preview: Boolean(withShare.preview),
                  punch_count: withShare.summary?.total_punch_list_items,
                },
              }),
            }).catch(() => undefined);
          }
        }
      })
      .catch(() => {
        /* persist failure must not block results UI */
      });
  }, []);

  // Prefill from Saved Jobs "Re-run research"
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem('regguard_job_prefill');
      if (!raw) return;
      sessionStorage.removeItem('regguard_job_prefill');
      const pre = JSON.parse(raw) as {
        address?: string;
        city?: string;
        state?: string;
        zip?: string;
        projectType?: string;
        email?: string;
      };
      setFormData((prev) => ({
        ...prev,
        address: pre.address || prev.address,
        city: pre.city || prev.city,
        state: pre.state || prev.state,
        zip: pre.zip || prev.zip,
        projectType: pre.projectType || prev.projectType,
        email: pre.email || prev.email,
      }));
      if (pre.address) {
        setExternalLocation({
          address: pre.address,
          city: pre.city,
          state: pre.state,
          zip: pre.zip,
        });
      }
      if (pre.email) setJobsEmail(pre.email);
    } catch {
      /* ignore bad prefill */
    }
  }, []);

  const runResearch = useCallback(async () => {
    const data = formDataRef.current;
    setError('');
    setLoading(true);
    setProgressStep('geocode');

    if (!data.address || !data.city || !data.state || !data.zip || !data.email) {
      setError('Please fill in address, city, state, ZIP, and email');
      setLoading(false);
      return;
    }

    const emailNorm = data.email.trim().toLowerCase();
    sessionStorage.setItem('userEmail', emailNorm);

    // Paid users get deeper research — allow longer wait
    let paid = sessionStorage.getItem('regguardPaid') === '1';
    let icReportPending = ['ic_project', 'ic_consultant', 'ic_annual'].includes(
      (sessionStorage.getItem('regguardTier') || '').toLowerCase()
    );
    try {
      const ent = await fetch(backendUrl(`/entitlement?email=${encodeURIComponent(emailNorm)}`));
      if (ent.ok) {
        const entData = await ent.json();
        paid = Boolean(entData.paid || entData.deep_research);
        if (paid) sessionStorage.setItem('regguardPaid', '1');
        const tiers = Array.isArray(entData.tiers)
          ? (entData.tiers as string[]).map((t) => String(t).toLowerCase())
          : [];
        const primary = String(entData.primary_tier || '').toLowerCase();
        const tier = tiers.find((t) =>
          ['ic_project', 'ic_consultant', 'ic_annual'].includes(t)
        ) || primary;
        if (['ic_project', 'ic_consultant', 'ic_annual'].includes(tier)) {
          sessionStorage.setItem('regguardTier', tier);
        }
        icReportPending = Boolean(entData.ic_report_pending) ||
          ['ic_project', 'ic_consultant', 'ic_annual'].includes(tier);
      }
    } catch {
      /* keep cached flag */
    }

    // Confirm before consuming the one-shot IC Project Report slot
    let generateIcReport = false;
    if (paid && icReportPending) {
      const tier = (sessionStorage.getItem('regguardTier') || '').toLowerCase();
      const annual = tier === 'ic_annual';
      generateIcReport = window.confirm(
        `Generate IC Project Report PDFs for:\n\n${data.address}, ${data.city}, ${data.state} ${data.zip}\n\n` +
          (annual
            ? 'This will create or replace the PDFs on your IC Annual order for this address. Cancel to research without updating PDFs.'
            : 'This will create or replace the PDFs on your IC Project purchase for this address. Cancel to research without generating PDFs.')
      );
    }

    const progressTimers = [
      window.setTimeout(() => setProgressStep('screen'), paid ? 2000 : 900),
      window.setTimeout(() => setProgressStep('punch'), paid ? 8000 : 2200),
    ];

    try {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), paid ? 130000 : 45000);

      const response = await fetch(backendUrl('/free-trial'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          address: `${data.address}, ${data.city}, ${data.state}, ${data.zip}`,
          zip: data.zip,
          project_type: data.projectType,
          email: emailNorm,
          phone: data.phone || undefined,
          generate_ic_report: generateIcReport,
        }),
      });
      window.clearTimeout(timeoutId);

      let payload: Record<string, unknown> = {};
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }

      if (response.status === 429) {
        setError(
          (payload.detail as string) ||
            'Too many requests — wait a minute and try again. No charge either way.'
        );
        return;
      }

      setProgressStep('punch');

      if (payload.paid) sessionStorage.setItem('regguardPaid', '1');
      if (payload.ic_pdfs_ready) {
        sessionStorage.setItem('icPdfsReady', '1');
        // Soft nudge: buyer can open My Orders for the three PDF downloads
        window.setTimeout(() => {
          if (window.confirm('Your IC Project Report PDFs are ready. Open My Orders to download?')) {
            window.location.href = '/orders';
          }
        }, 600);
      }

      if (payload.analysis_data && typeof payload.analysis_data === 'object') {
        const analysisData = {
          ...(payload.analysis_data as AnalysisData),
          ...(payload.share_url ? { share_url: payload.share_url as string } : {}),
          ...(payload.research_id ? { research_id: payload.research_id as string } : {}),
        };
        if (payload.research_depth && !analysisData.research_depth) {
          analysisData.research_depth = String(payload.research_depth);
        }
        const clientId =
          (payload.research_id as string) ||
          analysisData.research_id ||
          generateClientResearchId();
        showResults(analysisData, clientId, emailNorm);
      } else {
        const clientId = (payload.trial_id as string) || generateClientResearchId();
        showResults(
          buildClientInstantAnalysis({
            address: data.address,
            city: data.city,
            state: data.state,
            zip: data.zip,
            projectType: data.projectType,
          }),
          clientId,
          data.email
        );
      }
    } catch (err) {
      console.error(err);
      showResults(
        buildClientInstantAnalysis({
          address: data.address,
          city: data.city,
          state: data.state,
          zip: data.zip,
          projectType: data.projectType,
        }),
        generateClientResearchId(),
        data.email
      );
    } finally {
      progressTimers.forEach((t) => window.clearTimeout(t));
      setLoading(false);
    }
  }, [showResults]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await runResearch();
  };

  // Voice fill → form state
  useEffect(() => {
    const onFill = (ev: Event) => {
      const detail = (ev as CustomEvent<VoiceFillDetail>).detail;
      if (!detail) return;
      setExternalLocation({
        address: detail.address || undefined,
        city: detail.city || undefined,
        state: detail.state || undefined,
        zip: detail.zip || undefined,
      });
      setFormData((prev) => ({
        ...prev,
        address: detail.address || prev.address,
        city: detail.city || prev.city,
        state: detail.state || prev.state,
        zip: detail.zip || prev.zip,
        email: detail.email || prev.email,
        phone: detail.phone || prev.phone,
      }));
      if (detail.readyToRun) {
        setVoiceHint('Voice fields ready — tap Run research or submit below.');
      } else if (detail.transcript) {
        setVoiceHint('Listening captured — complete any missing fields, then run.');
      }
    };

    const onSubmit = () => {
      void runResearch();
    };

    window.addEventListener(VOICE_FILL_EVENT, onFill);
    window.addEventListener(VOICE_SUBMIT_EVENT, onSubmit);
    return () => {
      window.removeEventListener(VOICE_FILL_EVENT, onFill);
      window.removeEventListener(VOICE_SUBMIT_EVENT, onSubmit);
    };
  }, [runResearch]);

  return (
    <div id="free-trial-form">
      {showHero && (
        <div className="text-center mb-8">
          <h2 className="text-3xl md:text-4xl font-black text-white mb-3">Try RegGuard Free</h2>
          <p className="text-gray-300 text-base md:text-lg">
            One site. Seconds to a punch list. Or tap the mic and just say the address.
            {typeof window !== 'undefined' && sessionStorage.getItem('regguardPaid') === '1' ? (
              <span className="block mt-1 text-emerald-300/90 text-sm font-semibold">
                Contractor Pro active — this email runs deep scout research (may take up to ~2 min).
              </span>
            ) : null}
          </p>
        </div>
      )}

      <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-purple-500/30 rounded-2xl p-6 md:p-10">
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          <LocationPicker
            onLocationSelect={handleLocationSelect}
            disabled={loading}
            collapseMap={resultsOpen}
            externalValues={externalLocation}
          />

          <div>
            <label htmlFor="projectType" className="block text-white font-bold mb-2">
              Project type *
            </label>
            <select
              id="projectType"
              name="projectType"
              value={formData.projectType}
              onChange={handleInputChange}
              className="w-full px-4 py-3.5 min-h-[48px] bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500 text-base"
              disabled={loading}
            >
              <option value="data-center">Data Center</option>
              <option value="renewable">Solar / Wind / Battery</option>
              <option value="commercial">Commercial Building</option>
              <option value="industrial">Industrial / Manufacturing</option>
              <option value="utility">Utility / Substation</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="home-email" className="block text-white font-bold mb-2">
                Email *
              </label>
              <input
                id="home-email"
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="you@company.com"
                autoComplete="email"
                className="w-full px-4 py-3.5 min-h-[48px] bg-slate-700 border border-purple-500/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500 text-base"
                disabled={loading}
              />
            </div>
            <div>
              <label htmlFor="home-phone" className="block text-white font-bold mb-2">
                Phone <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <input
                id="home-phone"
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleInputChange}
                placeholder="(555) 123-4567"
                autoComplete="tel"
                className="w-full px-4 py-3.5 min-h-[48px] bg-slate-700 border border-purple-500/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500 text-base"
                disabled={loading}
              />
            </div>
          </div>

          {voiceHint && (
            <div className="flex gap-2 p-3 bg-emerald-500/15 border border-emerald-500/30 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
              <p className="text-emerald-200 text-sm">{voiceHint}</p>
            </div>
          )}

          {error && (
            <div className="flex gap-3 p-4 bg-red-500/20 border border-red-500/30 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          )}

          {loading && (
            <div className="rounded-xl border border-purple-500/30 bg-slate-900/70 p-4 space-y-3">
              {(
                [
                  ['geocode', MapPin],
                  ['screen', Search],
                  ['punch', ListChecks],
                ] as const
              ).map(([step, Icon]) => {
                const order: ProgressStep[] = ['geocode', 'screen', 'punch'];
                const activeIdx = order.indexOf(progressStep);
                const stepIdx = order.indexOf(step);
                const done = stepIdx < activeIdx;
                const active = step === progressStep;
                return (
                  <div
                    key={step}
                    className={`flex items-center gap-3 text-sm ${
                      active ? 'text-emerald-300' : done ? 'text-gray-400' : 'text-gray-500'
                    }`}
                  >
                    {active ? (
                      <Loader2 className="w-5 h-5 animate-spin text-emerald-400" />
                    ) : (
                      <Icon className="w-5 h-5" />
                    )}
                    <span className={active ? 'font-bold' : ''}>{PROGRESS_LABELS[step]}</span>
                  </div>
                );
              })}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full px-6 py-4 min-h-[56px] bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold text-lg rounded-xl transition shadow-lg shadow-green-500/20 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Analyzing site…' : 'Get Free Research Results'}
          </button>

          <p className="text-gray-400 text-sm text-center leading-relaxed">
            No credit card. Results in seconds. Text or email yourself from the results window.
          </p>
        </form>
      </div>

      {analysis && (
        <ResultsViewerModal
          isOpen={resultsOpen}
          onClose={() => setResultsOpen(false)}
          analysis={analysis}
          researchId={researchId}
          defaultEmail={formData.email}
          defaultPhone={formData.phone}
        />
      )}
    </div>
  );
}
