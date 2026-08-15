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
import {
  VOICE_FILL_EVENT,
  VOICE_SUBMIT_EVENT,
  type VoiceFillDetail,
} from '../voiceFillParse';

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

function readLastResearchForm(): Partial<{
  address: string;
  city: string;
  state: string;
  zip: string;
  projectType: string;
  email: string;
}> {
  try {
    const raw = sessionStorage.getItem('lastResearchForm');
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return {
      address: typeof parsed.address === 'string' ? parsed.address : undefined,
      city: typeof parsed.city === 'string' ? parsed.city : undefined,
      state: typeof parsed.state === 'string' ? parsed.state : undefined,
      zip: typeof parsed.zip === 'string' ? parsed.zip : undefined,
      projectType: typeof parsed.projectType === 'string' ? parsed.projectType : undefined,
      email: typeof parsed.email === 'string' ? parsed.email : undefined,
    };
  } catch {
    return {};
  }
}

function persistLastResearchForm(data: {
  address: string;
  city: string;
  state: string;
  zip: string;
  projectType: string;
  email: string;
}) {
  try {
    sessionStorage.setItem('lastResearchForm', JSON.stringify(data));
  } catch {
    /* ignore */
  }
}

export default function FreeTrialForm({
  showHero = false,
  defaultProjectType,
  lockProjectType = false,
}: {
  showHero?: boolean;
  /** Prefer this project type (e.g. data-center from /data-center hub) */
  defaultProjectType?: string;
  /** Hide selector and force defaultProjectType */
  lockProjectType?: boolean;
}) {
  const urlProjectType =
    typeof window !== 'undefined'
      ? (new URLSearchParams(window.location.search).get('projectType') ||
          new URLSearchParams(window.location.search).get('project_type') ||
          '')
          .trim()
          .toLowerCase()
      : '';
  const preferredType =
    defaultProjectType ||
    (urlProjectType === 'data-center' || urlProjectType === 'data_center'
      ? 'data-center'
      : urlProjectType) ||
    undefined;

  const [formData, setFormData] = useState({
    address: '',
    city: '',
    state: '',
    zip: '',
    projectType: preferredType || 'data-center',
    email: '',
    phone: '',
  });
  const [externalLocation, setExternalLocation] = useState<{
    address?: string;
    city?: string;
    state?: string;
    zip?: string;
  } | null>(null);
  /** Chrome ignores autocomplete=off; unlock on focus so fields stay blank on load. */
  const [fieldsUnlocked, setFieldsUnlocked] = useState(false);
  const unlockFields = () => setFieldsUnlocked(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState<ProgressStep>('geocode');
  const [resultsOpen, setResultsOpen] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [researchId, setResearchId] = useState<string | null>(null);
  const [voiceHint, setVoiceHint] = useState('');
  const [paidEntitled, setPaidEntitled] = useState(
    () => typeof window !== 'undefined' && sessionStorage.getItem('regguardPaid') === '1'
  );
  const [unlockBanner, setUnlockBanner] = useState(false);
  const autoUnlockTried = useRef(false);
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
    setError('');
  };

  const showResults = useCallback((analysisPayload: AnalysisData, id: string, email?: string) => {
    const analysisWithId: AnalysisData = { ...analysisPayload, research_id: id };
    sessionStorage.setItem('analysisResults', JSON.stringify(analysisWithId));
    sessionStorage.setItem('researchId', id);
    const mail = (email || formDataRef.current.email || '').trim().toLowerCase();
    if (mail) sessionStorage.setItem('userEmail', mail);
    const d = formDataRef.current;
    persistLastResearchForm({
      address: d.address,
      city: d.city,
      state: d.state,
      zip: d.zip,
      projectType: d.projectType,
      email: mail || d.email,
    });
    const depth = String(analysisWithId.research_depth || '').toLowerCase();
    if (depth === 'pro' || depth === 'pro_partial') {
      sessionStorage.removeItem('pendingDeepUnlock');
      setUnlockBanner(false);
    }
    setResearchId(id);
    setAnalysis(analysisWithId);
    setResultsOpen(true);
  }, []);

  const runResearch = useCallback(async () => {
    const data = formDataRef.current;
    setError('');
    setLoading(true);
    setProgressStep('geocode');

    if (!data.address || !data.city || !data.state || !data.zip || !data.email) {
      setError('Please confirm the address or finish filling in all fields of the address');
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
        if (paid) {
          sessionStorage.setItem('regguardPaid', '1');
          setPaidEntitled(true);
        }
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
          city: data.city,
          state: data.state,
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

      if (payload.paid) {
        sessionStorage.setItem('regguardPaid', '1');
        setPaidEntitled(true);
      }
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
        const analysis = payload.analysis_data as AnalysisData;
        if (payload.research_depth && !analysis.research_depth) {
          analysis.research_depth = String(payload.research_depth);
        }
        if (payload.job_id) {
          analysis.job_id = String(payload.job_id);
          try {
            sessionStorage.setItem('lastJobId', String(payload.job_id));
          } catch {
            /* ignore */
          }
        }
        const clientId =
          (payload.research_id as string) ||
          (analysis.research_id as string) ||
          generateClientResearchId();
        showResults(analysis, clientId, emailNorm);
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

  // After checkout return (?unlock=1): restore site for deepen — never on normal visits.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const unlockFromCheckout = params.get('unlock') === '1';
    const pending = sessionStorage.getItem('pendingDeepUnlock') === '1';

    if (!unlockFromCheckout && !pending) return;

    // Banner for any pending deepen; form fields only when returning from checkout.
    setUnlockBanner(true);
    if (!unlockFromCheckout) return;

    const last = readLastResearchForm();
    const email =
      (params.get('email') || sessionStorage.getItem('userEmail') || last.email || '')
        .trim()
        .toLowerCase();

    if (last.address || last.city || last.zip || email) {
      setFieldsUnlocked(true);
      setFormData((prev) => ({
        ...prev,
        address: last.address || prev.address,
        city: last.city || prev.city,
        state: last.state || prev.state,
        zip: last.zip || prev.zip,
        projectType: last.projectType || prev.projectType,
        email: email || prev.email,
      }));
      if (last.address) {
        setExternalLocation({
          address: last.address,
          city: last.city,
          state: last.state,
          zip: last.zip,
        });
      }
    }

    void (async () => {
      if (!email) return;
      try {
        const ent = await fetch(backendUrl(`/entitlement?email=${encodeURIComponent(email)}`));
        if (!ent.ok) return;
        const entData = await ent.json();
        const paid = Boolean(entData.paid || entData.deep_research);
        if (!paid) return;
        sessionStorage.setItem('regguardPaid', '1');
        setPaidEntitled(true);
        if (
          !autoUnlockTried.current &&
          (last.address || formDataRef.current.address) &&
          (last.city || formDataRef.current.city) &&
          (last.state || formDataRef.current.state) &&
          (last.zip || formDataRef.current.zip)
        ) {
          autoUnlockTried.current = true;
          window.setTimeout(() => {
            void runResearch();
          }, 400);
        }
      } catch {
        /* banner still available */
      }
    })();
  }, [runResearch]);

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
      {!resultsOpen && showHero && (
        <div className="text-center mb-8">
          <h2 className="text-3xl md:text-4xl font-black text-white mb-3">Try RegGuard Free</h2>
          <p className="text-gray-300 text-base md:text-lg">
            One site. Seconds to a citeable punch list you can forward.
            Or tap the mic and say the address.
            {typeof window !== 'undefined' && sessionStorage.getItem('regguardPaid') === '1' ? (
              <span className="block mt-1 text-emerald-300/90 text-sm font-semibold">
                Paid access active — this email runs deep scout research (may take up to ~2 min).
              </span>
            ) : (
              <span className="block mt-1 text-gray-400 text-sm">
                Free preview shows top actions — forward the list to unlock more, or upgrade for deep research.
              </span>
            )}
          </p>
        </div>
      )}

      {!resultsOpen && unlockBanner && (
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10">
          <p className="text-emerald-100 text-sm">
            Payment detected. Re-run this site with the same email to unlock deeper Contractor Pro /
            IC research results.
          </p>
          <button
            type="button"
            onClick={() => void runResearch()}
            disabled={loading}
            className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold whitespace-nowrap disabled:opacity-60"
          >
            {loading ? 'Deepening…' : 'Unlock deeper results'}
          </button>
        </div>
      )}

      {!resultsOpen && (
      <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-purple-500/30 rounded-2xl p-6 md:p-10">
        <form onSubmit={handleSubmit} className="space-y-5" noValidate autoComplete="off">
          <LocationPicker
            onLocationSelect={handleLocationSelect}
            disabled={loading}
            collapseMap={false}
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
              disabled={loading || lockProjectType}
            >
              <option value="data-center">Data Center</option>
              <option value="renewable">Solar / Wind / Battery</option>
              <option value="commercial">Commercial Building</option>
              <option value="industrial">Industrial / Manufacturing</option>
              <option value="utility">Utility / Substation</option>
              <option value="other">Other</option>
            </select>
            {lockProjectType && formData.projectType === 'data-center' && (
              <p className="text-xs text-indigo-300 mt-1">
                Locked to Data Center for parallel-track Bid Risk Receipt (AHJ + utility).
              </p>
            )}
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="home-email" className="block text-white font-bold mb-2">
                Email *
              </label>
              <input
                id="home-email"
                type="email"
                name="rg_site_email"
                value={formData.email}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, email: e.target.value }))
                }
                onFocus={unlockFields}
                placeholder="Email"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                readOnly={!fieldsUnlocked}
                data-lpignore="true"
                data-1p-ignore="true"
                data-form-type="other"
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
                name="rg_site_phone"
                value={formData.phone}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, phone: e.target.value }))
                }
                onFocus={unlockFields}
                placeholder="Phone"
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                readOnly={!fieldsUnlocked}
                data-lpignore="true"
                data-1p-ignore="true"
                data-form-type="other"
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
            {loading
              ? paidEntitled
                ? 'Running deep research…'
                : 'Analyzing site…'
              : paidEntitled
                ? 'Run deep research on this site'
                : 'Get Free Research Results'}
          </button>

          <p className="text-gray-400 text-sm text-center leading-relaxed">
            {paidEntitled
              ? 'Paid access active for this email — results include deeper scout research.'
              : 'No credit card. Results in seconds. Upgrade from the results window for deeper research.'}
          </p>
        </form>
      </div>
      )}

      {analysis && (
        <ResultsViewerModal
          isOpen={resultsOpen}
          onClose={() => {
            setResultsOpen(false);
            window.requestAnimationFrame(() => {
              document.getElementById('free-trial-form')?.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
              });
            });
          }}
          analysis={analysis}
          researchId={researchId}
          defaultEmail={formData.email}
          defaultPhone={formData.phone}
          canUnlockDeeper={
            paidEntitled &&
            analysis.research_depth !== 'pro' &&
            analysis.research_depth !== 'pro_partial'
          }
          onUnlockDeeper={() => {
            setResultsOpen(false);
            void runResearch();
          }}
          unlockLoading={loading}
        />
      )}
    </div>
  );
}
