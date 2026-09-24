/**
 * Shared free-trial form used on homepage (/) and /free-trial
 * Always opens ResultsViewerModal — even if API returns no analysis_data.
 * Listens for voice-fill events from VoiceCommandSystem.
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, CheckCircle2, Loader2, MapPin, Search, ListChecks } from 'lucide-react';
import { LocationPicker } from './LocationPicker';
import { backendUrl } from '../env';
import ResultsViewerModal, { AnalysisData } from './ResultsViewerModal';
import { buildClientInstantAnalysis } from './buildClientInstantAnalysis';
import { ErrorBoundary } from './ErrorBoundary';
import {
  VOICE_FILL_EVENT,
  VOICE_SUBMIT_EVENT,
  type VoiceFillDetail,
} from '../voiceFillParse';
import { preferUserLocality, zip5Of, cityForTxZip } from '../addressPrefer';
import {
  clearIcRunId,
  clearLastResearchForm,
  clearPendingIcReport,
  getOrCreateIcRunId,
  hasValidPendingIcReport,
  persistLastResearchForm,
  readLastResearchForm,
  setPendingIcReport,
} from '../icSiteBind';
import { trackStampEvent } from '../lib/trackStampEvent';
import { rememberReferralCode } from '../shareLinks';
import { getOwnerKey, persistSavedJob, setJobsEmail } from '../jobsOwner';
import { PRODUCT_COPY } from '../productCopy';

function generateClientResearchId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `ft-${crypto.randomUUID()}`;
  }
  return `ft-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

/** Once per document load — remount after Moratorium→Home must not re-wipe session results. */
let homeSessionInitDone = false;
/** Prevents useEffect from wiping the form a second time after useLayoutEffect on hard reload. */
let homeHardReloadWiped = false;

type ProgressStep = 'geocode' | 'screen' | 'punch';

const PROGRESS_LABELS: Record<ProgressStep, string> = {
  geocode: 'Finding the pin…',
  screen: 'Checking permits & environment…',
  punch: 'Building your Bid Risk Receipt…',
};

function usableLatLng(lat: unknown, lng: unknown): { lat: number; lng: number } | null {
  const la = Number(lat);
  const ln = Number(lng);
  if (!Number.isFinite(la) || !Number.isFinite(ln)) return null;
  if (Math.abs(la) < 1e-6 && Math.abs(ln) < 1e-6) return null;
  if (la < -90 || la > 90 || ln < -180 || ln > 180) return null;
  return { lat: la, lng: ln };
}

function coordsFromAnalysis(analysis: AnalysisData | null | undefined): { lat: number; lng: number } | null {
  if (!analysis) return null;
  const pi = analysis.project_info || ({} as NonNullable<AnalysisData['project_info']>);
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
    const hit = usableLatLng(la, ln);
    if (hit) return hit;
  }
  return null;
}

async function fetchEntitlementWithRetry(
  emailNorm: string,
  attempts = 3,
  site?: { address?: string; city?: string; state?: string; zip?: string }
): Promise<Record<string, unknown> | null> {
  const qs = new URLSearchParams({ email: emailNorm });
  if (site?.address) qs.set('address', site.address);
  if (site?.city) qs.set('city', site.city);
  if (site?.state) qs.set('state', site.state);
  if (site?.zip) qs.set('zip', site.zip);
  for (let i = 0; i < attempts; i += 1) {
    try {
      const ent = await fetch(backendUrl(`/entitlement?${qs.toString()}`));
      if (ent.ok) {
        return (await ent.json()) as Record<string, unknown>;
      }
    } catch {
      /* retry */
    }
    if (i < attempts - 1) {
      await new Promise((r) => window.setTimeout(r, 400 * (i + 1)));
    }
  }
  return null;
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
    lat: null as number | null,
    lng: null as number | null,
  });
  const [externalLocation, setExternalLocation] = useState<{
    address?: string;
    city?: string;
    state?: string;
    zip?: string;
    lat?: number | null;
    lng?: number | null;
  } | null>(null);
  const [locationResetKey, setLocationResetKey] = useState(0);
  /** After incomplete-run "Confirm pin", wait for map pin before re-researching */
  const pendingRerunAfterPinRef = useRef(false);
  const [fieldsUnlocked, setFieldsUnlocked] = useState(false);
  /** Delay mounting contact inputs so Chrome cannot autofill a pre-painted email field */
  const [contactFieldsReady, setContactFieldsReady] = useState(false);
  const contactAutofillPurgeUntilRef = useRef(0);
  /** Once the user touches email/phone, never run contact autofill wipe again. */
  const userEditedContactRef = useRef(false);
  const unlockFields = () => {
    setFieldsUnlocked(true);
    contactAutofillPurgeUntilRef.current = 0;
    userEditedContactRef.current = true;
  };
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
  const [entitlementTiers, setEntitlementTiers] = useState<string[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const raw = sessionStorage.getItem('regguardEntitlementTiers');
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.map((t) => String(t).toLowerCase()) : [];
    } catch {
      return [];
    }
  });
  const [icReportPending, setIcReportPending] = useState(false);
  const [unlockBanner, setUnlockBanner] = useState(false);
  const [quotaExceeded, setQuotaExceeded] = useState(false);
  const autoUnlockTried = useRef(false);
  const formDataRef = useRef(formData);
  formDataRef.current = formData;
  const navigate = useNavigate();

  useEffect(() => {
    try {
      const q = new URLSearchParams(window.location.search);
      const city = (q.get('city') || '').trim();
      const state = (q.get('state') || '').trim();
      const zip = (q.get('zip') || '').trim();
      const address = (q.get('address') || '').trim();
      if (city || state || zip || address) {
        setFormData((prev) => ({
          ...prev,
          ...(address ? { address } : {}),
          ...(city ? { city } : {}),
          ...(state ? { state } : {}),
          ...(zip ? { zip } : {}),
        }));
        if (city || address) {
          setExternalLocation({
            ...(address ? { address } : {}),
            ...(city ? { city } : {}),
            ...(state ? { state } : {}),
            ...(zip ? { zip } : {}),
          });
        }
      }
    } catch {
      /* ignore */
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleLocationSelect = (
    address: string,
    city: string,
    state: string,
    zip: string,
    lat: number,
    lng: number
  ) => {
    const pin = usableLatLng(lat, lng);
    setFormData((prev) => ({
      ...prev,
      address,
      city,
      state,
      zip,
      lat: pin ? pin.lat : null,
      lng: pin ? pin.lng : null,
    }));
    setExternalLocation({
      address,
      city,
      state,
      zip,
      lat: pin?.lat ?? null,
      lng: pin?.lng ?? null,
    });
    setError('');
    setQuotaExceeded(false);
  };

  const startNewSite = () => {
    const keepEmail = formData.email;
    clearLastResearchForm();
    clearPendingIcReport();
    try {
      sessionStorage.removeItem('pendingDeepUnlock');
      sessionStorage.removeItem('icForceOnce');
      sessionStorage.removeItem('icPdfsReady');
    } catch {
      /* ignore */
    }
    setUnlockBanner(false);
    setExternalLocation(null);
    setLocationResetKey((k) => k + 1);
    setFormData({
      address: '',
      city: '',
      state: '',
      zip: '',
      projectType: preferredType || 'data-center',
      email: keepEmail,
      phone: '',
      lat: null,
      lng: null,
    });
    setError('');
    setVoiceHint('New site — enter a fresh address (pin stays editable unless you Lock).');
    try {
      const url = new URL(window.location.href);
      url.searchParams.delete('run_ic');
      url.searchParams.delete('unlock');
      window.history.replaceState({}, '', url.pathname + (url.search || ''));
    } catch {
      /* ignore */
    }
  };

  const showResults = useCallback((analysisPayload: AnalysisData, id: string, email?: string) => {
    const rid = (id || analysisPayload.research_id || '').trim();
    const shareFromPayload = (analysisPayload.share_url || '').trim();
    const share =
      shareFromPayload.includes('/r/') && !shareFromPayload.endsWith('/r/')
        ? shareFromPayload
        : rid && !rid.startsWith('ephemeral-')
          ? `https://app.regguardagent.com/r/${encodeURIComponent(rid)}`
          : shareFromPayload || undefined;
    const analysisWithId: AnalysisData = {
      ...analysisPayload,
      research_id: rid || analysisPayload.research_id,
      ...(share ? { share_url: share } : {}),
    };
    const refCode = String((analysisPayload as { referral_code?: string }).referral_code || '').trim();
    if (refCode) rememberReferralCode(refCode);
    sessionStorage.setItem('analysisResults', JSON.stringify(analysisWithId));
    sessionStorage.setItem('researchId', id);
    const mail = (email || formDataRef.current.email || '').trim().toLowerCase();
    if (mail) setJobsEmail(mail);
    const d = formDataRef.current;
    persistLastResearchForm({
      address: d.address,
      city: d.city,
      state: d.state,
      zip: d.zip,
      projectType: d.projectType,
      email: mail || d.email,
      lat: d.lat,
      lng: d.lng,
    });
    void persistSavedJob({
      owner_email: mail,
      address: analysisWithId.project_info?.address || d.address,
      city: analysisWithId.project_info?.city || d.city,
      state: analysisWithId.project_info?.state || d.state,
      zip: analysisWithId.project_info?.zip || d.zip,
      project_type: analysisWithId.project_info?.type || d.projectType,
      last_research_id: rid || id,
      share_url: analysisWithId.share_url,
      // Never pass prior job_id — stale ids were overwriting other sites
      phone: d.phone,
      last_stamp_grade: analysisWithId.regguard_stamp?.grade || analysisWithId.stamp_grade,
      punch_count: analysisWithId.punch_list?.punch_list?.length,
      preview: Boolean(analysisWithId.preview),
    }).then((result) => {
      if (result.id) {
        analysisWithId.job_id = result.id;
        try {
          sessionStorage.setItem('lastJobId', result.id);
        } catch {
          /* ignore */
        }
      } else if (result.error && mail) {
        console.warn('[RegGuard] Saved Jobs persist failed:', result.error);
      }
    });
    const depth = String(analysisWithId.research_depth || '').toLowerCase();
    if (depth === 'pro' || depth === 'pro_partial') {
      sessionStorage.removeItem('pendingDeepUnlock');
      setUnlockBanner(false);
    }
    setResearchId(id);
    setAnalysis(analysisWithId);
    setResultsOpen(true);
    // Keep formData + map pin aligned with what research actually used
    {
      const pin = coordsFromAnalysis(analysisWithId) || usableLatLng(d.lat, d.lng);
      const pi = analysisWithId.project_info;
      const nextAddress = (pi?.address || d.address || '').trim();
      const nextCity = (pi?.city || d.city || '').trim();
      const nextState = (pi?.state || d.state || '').trim();
      const nextZip = (pi?.zip || d.zip || '').trim();
      if (nextAddress || nextCity || pin) {
        setFormData((prev) => ({
          ...prev,
          ...(nextAddress ? { address: nextAddress } : {}),
          ...(nextCity ? { city: nextCity } : {}),
          ...(nextState ? { state: nextState } : {}),
          ...(nextZip ? { zip: nextZip } : {}),
          lat: pin?.lat ?? prev.lat,
          lng: pin?.lng ?? prev.lng,
        }));
        setExternalLocation({
          address: nextAddress || undefined,
          city: nextCity || undefined,
          state: nextState || undefined,
          zip: nextZip || undefined,
          lat: pin?.lat ?? null,
          lng: pin?.lng ?? null,
        });
      }
    }
    try {
      sessionStorage.setItem('resultsOpen', '1');
    } catch {
      /* ignore */
    }
    // Blank demand funnel: count successful runs (ephemeral/client fallbacks still count as runs)
    trackStampEvent('research_run', {
      researchId: rid || id,
      zip: analysisWithId.project_info?.zip || formDataRef.current.zip,
      stampGrade: analysisWithId.regguard_stamp?.grade || analysisWithId.stamp_grade,
      stampFingerprint: analysisWithId.regguard_stamp?.fingerprint,
      channel: 'free_trial',
      meta: {
        depth: depth || 'instant',
        project_type: formDataRef.current.projectType || '',
      },
    });
  }, []);

  const runResearch = useCallback(async () => {
    const data = formDataRef.current;
    setError('');
    setQuotaExceeded(false);
    setProgressStep('geocode');

    if (!data.address || !data.city || !data.state || !data.zip || !data.email) {
      setError('Enter street, city, state, ZIP, and email.');
      return;
    }

    const weakStreet =
      /^#?\d{1,6}[A-Za-z]?$/.test(data.address.trim()) ||
      data.address.trim().length < 5 ||
      /^(apt|unit|suite|ste)\b/i.test(data.address.trim());
    if (weakStreet) {
      setError(
        'Street looks incomplete (e.g. "#130"). Enter the full street — e.g. 1201 14th St — with Plano and ZIP 75074.'
      );
      return;
    }

    const z = zip5Of(data.zip);
    const mapped = cityForTxZip(z);
    if (mapped && data.city.trim().toLowerCase() !== mapped.toLowerCase()) {
      const fix = window.confirm(
        `ZIP ${z} is usually ${mapped}, but the form says ${data.city}.\n\n` +
          `Use ${mapped}, TX ${z}?\n\nOK = fix to ${mapped}  ·  Cancel = stop and edit`
      );
      if (!fix) {
        setError(`Fix city to ${mapped} (or correct the ZIP) before running.`);
        return;
      }
      setFormData((prev) => ({ ...prev, city: mapped, state: 'TX', zip: z }));
      formDataRef.current = { ...formDataRef.current, city: mapped, state: 'TX', zip: z };
    }

    setLoading(true);

    // Re-read after any ZIP/city correction above
    const fixed = formDataRef.current;
    const emailNorm = fixed.email.trim().toLowerCase();
    setJobsEmail(emailNorm);

    // Paid users get deeper research — allow longer wait
    let paid = sessionStorage.getItem('regguardPaid') === '1';
    let icReportPending = ['ic_project', 'ic_consultant', 'ic_annual'].includes(
      (sessionStorage.getItem('regguardTier') || '').toLowerCase()
    );
    const entData = await fetchEntitlementWithRetry(emailNorm, 3, {
      address: fixed.address,
      city: fixed.city,
      state: fixed.state,
      zip: fixed.zip,
    });
    if (entData) {
      paid = Boolean(entData.paid || entData.deep_research);
      if (paid) {
        sessionStorage.setItem('regguardPaid', '1');
        setPaidEntitled(true);
      }
      const tiers = Array.isArray(entData.tiers)
        ? (entData.tiers as string[]).map((t) => String(t).toLowerCase())
        : [];
      setEntitlementTiers(tiers);
      try {
        sessionStorage.setItem('regguardEntitlementTiers', JSON.stringify(tiers));
      } catch {
        /* ignore */
      }
      const primary = String(entData.primary_tier || '').toLowerCase();
      const tier =
        tiers.find((t) => ['ic_project', 'ic_consultant', 'ic_annual'].includes(t)) || primary;
      if (['ic_project', 'ic_consultant', 'ic_annual'].includes(tier)) {
        sessionStorage.setItem('regguardTier', tier);
      }
      // Site-bound: only pending when THIS site can use an IC credit
      const icSite = (entData.ic_site || {}) as Record<string, unknown>;
      icReportPending = Boolean(icSite.allowed);
      setIcReportPending(icReportPending);
    }

    // Premortem F9: skip-confirm path only via one-shot icForceOnce (set from ?run_ic=1)
    // Premortem F2: always show address confirm before consuming slot
    let generateIcReport = false;
    let forceOnce = false;
    try {
      forceOnce = sessionStorage.getItem('icForceOnce') === '1';
    } catch {
      forceOnce = false;
    }
    const forceIc = Boolean(forceOnce && hasValidPendingIcReport() && paid && icReportPending);
    // Normalize so IC confirm never shows Dallas when ZIP is Plano 75074
    const siteNorm = preferUserLocality({
      userStreet: fixed.address,
      userCity: fixed.city,
      userState: fixed.state,
      userZip: fixed.zip,
    });
    const siteChip = `${siteNorm.street || fixed.address}, ${siteNorm.city || fixed.city}, ${
      siteNorm.state || fixed.state
    } ${siteNorm.zip || fixed.zip}`;
    const dataForApi = {
      ...fixed,
      address: siteNorm.street || fixed.address,
      city: siteNorm.city || fixed.city,
      state: siteNorm.state || fixed.state,
      zip: siteNorm.zip || fixed.zip,
    };

    // Re-fetch entitlement with normalized site (authoritative for dialog)
    const siteEnt = await fetchEntitlementWithRetry(emailNorm, 2, {
      address: dataForApi.address,
      city: dataForApi.city,
      state: dataForApi.state,
      zip: dataForApi.zip,
    });
    const icSite = ((siteEnt || entData)?.ic_site || {}) as {
      allowed?: boolean;
      mode?: string;
      message?: string;
      bound_site?: string;
    };
    const icAllowed = Boolean(icSite.allowed);
    icReportPending = icAllowed;
    setIcReportPending(icAllowed);

    if (paid && icAllowed) {
      const msg =
        icSite.message ||
        `Generate IC Diligence Bundle for:\n\n${siteChip}\n\nOK uses your IC credit for this address only.`;
      if (forceIc) {
        generateIcReport = window.confirm(msg);
        try {
          sessionStorage.removeItem('icForceOnce');
        } catch {
          /* ignore */
        }
        if (generateIcReport) {
          clearPendingIcReport();
        }
      } else {
        generateIcReport = window.confirm(msg);
        if (!generateIcReport) {
          clearPendingIcReport();
        }
      }
    } else if (
      paid &&
      !icAllowed &&
      String(icSite.mode || '') === 'need_purchase' &&
      (forceOnce ||
        hasValidPendingIcReport() ||
        entitlementTiers.some((t) => String(t).includes('ic')) ||
        ['ic_project', 'ic_consultant', 'ic_annual'].includes(
          (sessionStorage.getItem('regguardTier') || '').toLowerCase()
        ))
    ) {
      // Prior IC purchase is for a different site — new address requires a new $1,500 payment
      const buy = window.confirm(
        icSite.message ||
          `IC Project is $1,500 per site.\n\n${siteChip}\n\nOK opens Checkout for this address. Cancel runs research without the counsel ZIP.`
      );
      try {
        sessionStorage.removeItem('icForceOnce');
      } catch {
        /* ignore */
      }
      clearPendingIcReport();
      if (buy) {
        persistLastResearchForm({
          address: dataForApi.address,
          city: dataForApi.city,
          state: dataForApi.state,
          zip: dataForApi.zip,
          projectType: dataForApi.projectType,
          email: emailNorm,
          lat: dataForApi.lat,
          lng: dataForApi.lng,
        });
        setLoading(false);
        navigate(
          `/checkout/ic_project?email=${encodeURIComponent(emailNorm)}&from=new_site`
        );
        return;
      }
    } else if (hasValidPendingIcReport() && !icAllowed) {
      clearPendingIcReport();
    }
    if (generateIcReport) {
      setProgressStep('punch');
    }

    const progressTimers = [
      window.setTimeout(() => setProgressStep('screen'), paid ? 2000 : 900),
      window.setTimeout(() => setProgressStep('punch'), paid ? 8000 : 2200),
    ];

    try {
      const controller = new AbortController();
      // Premortem F4: IC path needs more headroom than Pro deepen
      const timeoutMs = generateIcReport ? 180000 : paid ? 130000 : 45000;
      const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
      const icKey = generateIcReport ? getOrCreateIcRunId() : undefined;

      const response = await fetch(backendUrl('/free-trial'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          address: dataForApi.address,
          zip: dataForApi.zip,
          city: dataForApi.city,
          state: dataForApi.state,
          project_type: dataForApi.projectType,
          email: emailNorm,
          phone: dataForApi.phone || undefined,
          generate_ic_report: generateIcReport,
          ic_idempotency_key: icKey,
          owner_key: getOwnerKey() || undefined,
          ...(dataForApi.lat != null && dataForApi.lng != null
            ? { latitude: dataForApi.lat, longitude: dataForApi.lng }
            : {}),
        }),
      });
      window.clearTimeout(timeoutId);
      if (generateIcReport) {
        clearIcRunId();
      }

      let payload: Record<string, unknown> = {};
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }

      if (response.status === 429) {
        setQuotaExceeded(true);
        setError(
          (payload.detail as string) ||
            'Free monthly lookups used up for this email. Start Estimator / Permit Runner ($79/mo) or Contractor Pro ($149/mo) — no charge for this blocked run.'
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
        // Keep results open in-app — PDF banner lives on the results panel (no hard redirect).
      } else {
        // Free / Pro runs must not inherit a prior IC "ready" flag
        try {
          const ad = payload.analysis_data as { depth_tier?: string; research_depth?: string } | undefined;
          const dt = String(ad?.depth_tier || '').toLowerCase();
          const rd = String(ad?.research_depth || payload.research_depth || '').toLowerCase();
          if (dt !== 'ic_full' && rd !== 'ic' && rd !== 'ic_full') {
            sessionStorage.removeItem('icPdfsReady');
          }
        } catch {
          sessionStorage.removeItem('icPdfsReady');
        }
      }

      if (payload.analysis_data && typeof payload.analysis_data === 'object') {
        const analysis = payload.analysis_data as AnalysisData;
        if (payload.research_depth && !analysis.research_depth) {
          analysis.research_depth = String(payload.research_depth);
        }
        if (payload.ic_pdfs_ready) {
          (analysis as AnalysisData & { ic_pdfs_ready?: boolean }).ic_pdfs_ready = true;
          // Server sends one IC PDF-ready email — do not also POST /research/send-email
          // (that was causing multiple Bid Risk Receipt duplicates).
        }
        // Prefer server share URL so email/SMS never say "unavailable"
        const payloadShare = String(payload.share_url || '').trim();
        if (payloadShare.includes('/r/')) {
          analysis.share_url = payloadShare;
        }
        if (payload.research_id && !analysis.research_id) {
          analysis.research_id = String(payload.research_id);
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

  // Incomplete-run "Confirm pin" — once the map settles a usable pin, re-run automatically
  useEffect(() => {
    if (!pendingRerunAfterPinRef.current) return;
    const pin = usableLatLng(formData.lat, formData.lng);
    if (!pin) return;
    pendingRerunAfterPinRef.current = false;
    setVoiceHint('Pin confirmed — re-running deep research…');
    const t = window.setTimeout(() => {
      void runResearch();
    }, 150);
    return () => window.clearTimeout(t);
  }, [formData.lat, formData.lng, runResearch]);

  const restoreSiteLocation = useCallback(
    (fromAnalysis?: AnalysisData | null) => {
      const d = formDataRef.current;
      const pi = fromAnalysis?.project_info;
      const address = (pi?.address || d.address || '').trim();
      const city = (pi?.city || d.city || '').trim();
      const state = (pi?.state || d.state || '').trim();
      const zip = (pi?.zip || d.zip || '').trim();
      const pin = usableLatLng(d.lat, d.lng) || coordsFromAnalysis(fromAnalysis);
      setFormData((prev) => ({
        ...prev,
        ...(address ? { address } : {}),
        ...(city ? { city } : {}),
        ...(state ? { state } : {}),
        ...(zip ? { zip } : {}),
        lat: pin?.lat ?? prev.lat,
        lng: pin?.lng ?? prev.lng,
      }));
      setExternalLocation({
        address: address || undefined,
        city: city || undefined,
        state: state || undefined,
        zip: zip || undefined,
        lat: pin?.lat ?? null,
        lng: pin?.lng ?? null,
      });
      return { address, city, state, zip, pin };
    },
    []
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await runResearch();
  };

  // Hard reload = blank slate once per document load. Soft remount (Moratorium → Home) keeps results.
  useLayoutEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const unlockFromCheckout = params.get('unlock') === '1';
    const runIc = params.get('run_ic') === '1';
    const keepForCheckout = unlockFromCheckout || runIc;
    const nav = performance.getEntriesByType?.('navigation')?.[0] as
      | PerformanceNavigationTiming
      | undefined;
    // Note: nav.type stays "reload" for the whole document life — do not re-wipe on remount.
    const isHardReload = nav?.type === 'reload';
    const alreadyInitThisDocument = homeSessionInitDone;
    homeSessionInitDone = true;

    if (keepForCheckout) {
      setContactFieldsReady(true);
      return;
    }

    // Soft client-side remount or first paint after soft nav: keep sticky results
    if (alreadyInitThisDocument || !isHardReload) {
      setContactFieldsReady(true);
      return;
    }

    homeHardReloadWiped = true;
    try {
      sessionStorage.removeItem('userEmail');
      sessionStorage.removeItem('analysisResults');
      sessionStorage.removeItem('researchId');
      sessionStorage.removeItem('lastResearchForm');
      sessionStorage.removeItem('pendingDeepUnlock');
      sessionStorage.removeItem('icForceOnce');
      sessionStorage.removeItem('icPdfsReady');
      sessionStorage.removeItem('resultsOpen');
    } catch {
      /* ignore */
    }
    setAnalysis(null);
    setResearchId(null);
    setResultsOpen(false);
    setExternalLocation(null);
    setFieldsUnlocked(false);
    userEditedContactRef.current = false;
    setFormData((prev) => ({
      ...prev,
      address: '',
      city: '',
      state: '',
      zip: '',
      email: '',
      phone: '',
      lat: null,
      lng: null,
    }));
    setLocationResetKey((k) => k + 1);
    // Contact fields mount after a short delay so Chrome cannot paint-autofill into them.
    // Do NOT keep wiping email/phone after mount — that was clearing user input mid-typing.
    setContactFieldsReady(false);
    const tReady = window.setTimeout(() => setContactFieldsReady(true), 120);
    return () => {
      window.clearTimeout(tReady);
    };
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const unlockFromCheckout = params.get('unlock') === '1';
    const runIc = params.get('run_ic') === '1';
    const resume = params.get('resume') === '1';
    const explicitRestore = unlockFromCheckout || runIc;
    const nav = performance.getEntriesByType?.('navigation')?.[0] as
      | PerformanceNavigationTiming
      | undefined;
    const isHardReload = nav?.type === 'reload';
    // Only blank-slate on the first hard-reload mount — layout effect already wiped once.
    const wipeHardReloadSession =
      isHardReload &&
      !homeHardReloadWiped &&
      !sessionStorage.getItem('analysisResults') &&
      !sessionStorage.getItem('researchId');

    // Soft nav / resume: restore last results and re-open the panel
    try {
      const stored = sessionStorage.getItem('analysisResults');
      const rid = sessionStorage.getItem('researchId') || '';
      const wantOpen =
        resume ||
        sessionStorage.getItem('resultsOpen') === '1' ||
        Boolean(stored);
      if (stored && !wipeHardReloadSession && !homeHardReloadWiped) {
        const parsed = JSON.parse(stored) as AnalysisData;
        setAnalysis(parsed);
        setResearchId(rid || parsed.research_id || null);
        if (wantOpen && !explicitRestore) {
          setResultsOpen(true);
          try {
            sessionStorage.setItem('resultsOpen', '1');
          } catch {
            /* ignore */
          }
        }
        if (resume) {
          const url = new URL(window.location.href);
          url.searchParams.delete('resume');
          window.history.replaceState({}, '', url.pathname + (url.search || ''));
        }
      }
    } catch {
      /* ignore */
    }

    if (!explicitRestore) {
      if (wipeHardReloadSession) {
        homeHardReloadWiped = true;
        clearLastResearchForm();
        clearPendingIcReport();
        try {
          sessionStorage.removeItem('pendingDeepUnlock');
          sessionStorage.removeItem('icForceOnce');
          sessionStorage.removeItem('icPdfsReady');
          sessionStorage.removeItem('userEmail');
          localStorage.removeItem('regguard_jobs_email');
          sessionStorage.removeItem('analysisResults');
          sessionStorage.removeItem('researchId');
          sessionStorage.removeItem('resultsOpen');
        } catch {
          /* ignore */
        }
        setUnlockBanner(false);
        setExternalLocation(null);
        setFieldsUnlocked(false);
        setLocationResetKey((k) => k + 1);
        setFormData((prev) => ({
          ...prev,
          address: '',
          city: '',
          state: '',
          zip: '',
          phone: '',
          lat: null,
          lng: null,
          email: '',
        }));
        setAnalysis(null);
        setResearchId(null);
        setResultsOpen(false);
        if (params.has('email')) {
          try {
            const url = new URL(window.location.href);
            url.searchParams.delete('email');
            window.history.replaceState({}, '', url.pathname + (url.search || ''));
          } catch {
            /* ignore */
          }
        }
      }
      return;
    }

    setUnlockBanner(true);

    const last = readLastResearchForm();
    // Premortem F7: checkout success email wins over stale form email
    const email = (
      params.get('email') ||
      sessionStorage.getItem('userEmail') ||
      (runIc ? '' : last.email) ||
      ''
    )
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

    if (runIc) {
      try {
        setPendingIcReport(true);
        sessionStorage.setItem('icForceOnce', '1');
        sessionStorage.setItem('regguardPaid', '1');
        sessionStorage.setItem('pendingDeepUnlock', '1');
        if (email) sessionStorage.setItem('userEmail', email);
      } catch {
        /* ignore */
      }
    }

    void (async () => {
      if (!email) return;
      const siteHint = {
        address: last.address || formDataRef.current.address,
        city: last.city || formDataRef.current.city,
        state: last.state || formDataRef.current.state,
        zip: last.zip || formDataRef.current.zip,
      };
      const entData = await fetchEntitlementWithRetry(email, 3, siteHint);
      if (!entData) return;
      const paid = Boolean(entData.paid || entData.deep_research);
      if (!paid) return;
      sessionStorage.setItem('regguardPaid', '1');
      setPaidEntitled(true);
      const tiers = Array.isArray(entData.tiers)
        ? (entData.tiers as string[]).map((t) => String(t).toLowerCase())
        : [];
      setEntitlementTiers(tiers);
      try {
        sessionStorage.setItem('regguardEntitlementTiers', JSON.stringify(tiers));
      } catch {
        /* ignore */
      }
      const primary = String(entData.primary_tier || '').toLowerCase();
      const tier =
        tiers.find((t) => ['ic_project', 'ic_consultant', 'ic_annual'].includes(t)) || primary;
      if (tier) sessionStorage.setItem('regguardTier', tier);
      const icSite = (entData.ic_site || {}) as { allowed?: boolean };
      // Only mark pending when THIS site can consume an IC credit (not any prior purchase)
      setIcReportPending(Boolean(icSite.allowed) || Boolean(entData.ic_report_pending));

      const readySite =
        (last.address || formDataRef.current.address) &&
        (last.city || formDataRef.current.city) &&
        (last.state || formDataRef.current.state) &&
        (last.zip || formDataRef.current.zip);

      const shouldAuto =
        Boolean(readySite) &&
        !autoUnlockTried.current &&
        (runIc || (unlockFromCheckout && !hasValidPendingIcReport()));

      if (shouldAuto) {
        autoUnlockTried.current = true;
        try {
          const url = new URL(window.location.href);
          url.searchParams.delete('run_ic');
          window.history.replaceState({}, '', url.pathname + (url.search || ''));
        } catch {
          /* ignore */
        }
        window.setTimeout(() => {
          void runResearch();
        }, 450);
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
      {!resultsOpen && analysis && (
        <div className="mb-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <p className="text-sm text-emerald-100">
            Last site results are still saved in this browser tab.
          </p>
          <button
            type="button"
            onClick={() => {
              setResultsOpen(true);
              try {
                sessionStorage.setItem('resultsOpen', '1');
              } catch {
                /* ignore */
              }
            }}
            className="px-4 py-2.5 min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold"
          >
            Re-open results
          </button>
        </div>
      )}

      {!resultsOpen && showHero && (
        <div className="text-center mb-8">
          <h2 className="text-3xl md:text-4xl font-black text-white mb-3">Try Reg Guard free</h2>
          <p className="text-gray-300 text-base md:text-lg">
            One site. Seconds to a forwardable Bid Risk Receipt — not a quote.
            Or tap the mic and say the address.
            {typeof window !== 'undefined' && sessionStorage.getItem('regguardPaid') === '1' ? (
              <span className="block mt-1 text-emerald-300/90 text-sm font-semibold">
                Paid access active — Pro runs local confirm + light scout (may take ~1–2 min). IC adds
                the Diligence Bundle ZIP.
              </span>
            ) : (
              <span className="block mt-1 text-gray-400 text-sm">
                Free preview shows top actions — Estimator / Permit Runner unlocks the full Receipt;
                Contractor Pro adds CSV + city pack; IC unlocks the Diligence Bundle.
              </span>
            )}
          </p>
        </div>
      )}

      {!resultsOpen && unlockBanner && (
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10">
          <p className="text-emerald-100 text-sm">
            {typeof window !== 'undefined' &&
            (hasValidPendingIcReport() ||
              new URLSearchParams(window.location.search).get('run_ic') === '1')
              ? `Payment detected — ready to generate IC Diligence Bundle for ${
                  formData.address
                    ? `${formData.address}, ${formData.city}, ${formData.state} ${formData.zip}`
                    : 'the saved site'
                }. Confirm the address when prompted — you will get the counsel ZIP (memo + boardroom PDF + DOCX + CSVs).`
              : 'Payment detected. Re-run this site with the same email to unlock deeper Contractor Pro / IC research results.'}
          </p>
          <div className="flex flex-col sm:flex-row gap-2 shrink-0">
            <button
              type="button"
              onClick={() => {
                try {
                  if (
                    sessionStorage.getItem('regguardTier')?.toLowerCase().includes('ic') ||
                    hasValidPendingIcReport() ||
                    new URLSearchParams(window.location.search).get('run_ic') === '1'
                  ) {
                    setPendingIcReport(true);
                    sessionStorage.setItem('icForceOnce', '1');
                  }
                } catch {
                  /* ignore */
                }
                void runResearch();
              }}
              disabled={loading}
              className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold whitespace-nowrap disabled:opacity-60"
            >
              {loading
                ? 'Generating IC report…'
                : hasValidPendingIcReport() ||
                    new URLSearchParams(window.location.search).get('run_ic') === '1'
                  ? 'Generate IC Report now'
                  : 'Unlock deeper results'}
            </button>
            <button
              type="button"
              onClick={startNewSite}
              disabled={loading}
              className="px-4 py-2.5 rounded-lg border border-slate-500 bg-slate-900/60 hover:bg-slate-800 text-white text-sm font-semibold whitespace-nowrap disabled:opacity-60"
            >
              Different site
            </button>
          </div>
        </div>
      )}

      {/* Keep form mounted while results are open so address + pin state survive Confirm / re-run */}
      <div
        className={`bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-purple-500/30 rounded-2xl p-6 md:p-10 ${
          resultsOpen && analysis ? 'hidden' : ''
        }`}
        aria-hidden={Boolean(resultsOpen && analysis)}
      >
        <form onSubmit={handleSubmit} className="space-y-5" noValidate autoComplete="off">
          <h2 className="text-xl sm:text-2xl font-black text-white leading-tight">
            {PRODUCT_COPY.formHeading}
          </h2>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={startNewSite}
              disabled={loading}
              className="text-sm text-emerald-300 hover:text-emerald-200 font-semibold underline-offset-2 hover:underline disabled:opacity-50"
            >
              Clear &amp; start over
            </button>
          </div>
          <LocationPicker
            onLocationSelect={handleLocationSelect}
            disabled={loading}
            collapseMap={Boolean(resultsOpen && analysis)}
            externalValues={externalLocation}
            resetKey={locationResetKey}
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
              autoComplete="off"
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

          {/*
            Contact fields live OUTSIDE the site-address form association so Chrome/Safari
            contact autofill (email/phone → home address) cannot rewrite the jobsite or pin.
          */}
        </form>

        <div className="mt-5 space-y-5" data-rg-contact-fields autoComplete="off">
          {!contactFieldsReady ? (
            <div className="h-[7.5rem] rounded-lg border border-slate-700/60 bg-slate-800/40" aria-hidden />
          ) : (
            <>
          <div>
            <label htmlFor="home-email" className="block text-white font-bold mb-2">
              Email *
            </label>
            <input
              key={`home-email-${locationResetKey}`}
              id="home-email"
              type="text"
              inputMode="email"
              name={`rg_contact_email_${locationResetKey}`}
              value={formData.email}
              onChange={(e) => {
                userEditedContactRef.current = true;
                contactAutofillPurgeUntilRef.current = 0;
                setFormData((prev) => ({ ...prev, email: e.target.value }));
              }}
              onFocus={unlockFields}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  void runResearch();
                }
              }}
              placeholder=""
              autoComplete="new-password"
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
            <p className="text-xs text-gray-400 mt-2">
              Email is required to run a lookup. SMS is optional after results (separate consent).
            </p>
          </div>
            </>
          )}
        </div>

        <form
          onSubmit={handleSubmit}
          className="mt-5 space-y-5"
          noValidate
          autoComplete="off"
        >
          {voiceHint && (
            <div className="flex gap-2 p-3 bg-emerald-500/15 border border-emerald-500/30 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
              <p className="text-emerald-200 text-sm">{voiceHint}</p>
            </div>
          )}

          {error && (
            <div className="flex gap-3 p-4 bg-red-500/20 border border-red-500/30 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1 space-y-3">
                <p className="text-red-300 text-sm">{error}</p>
                {quotaExceeded && (
                  <div className="flex flex-col sm:flex-row gap-2">
                    <button
                      type="button"
                      onClick={() => navigate('/checkout/partner')}
                      className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold"
                    >
                      Start Estimator / Permit Runner — $79/mo
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate('/checkout/contractor_pro')}
                      className="px-4 py-2.5 rounded-lg border border-slate-500 bg-slate-900/60 hover:bg-slate-800 text-white text-sm font-semibold"
                    >
                      Contractor Pro — $149/mo
                    </button>
                  </div>
                )}
              </div>
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
                : 'Get my Bid Risk Receipt'}
          </button>

          <p className="text-gray-400 text-sm text-center leading-relaxed">
            {paidEntitled
              ? 'Paid access active for this email — results include deeper scout research.'
              : 'No credit card stored by Reg Guard (Stripe handles paid upgrades). Results in seconds.'}
          </p>
        </form>
      </div>

      {analysis && (
        <ErrorBoundary
          onReset={() => {
            setResultsOpen(false);
          }}
        >
          <ResultsViewerModal
            isOpen={resultsOpen}
            onClose={() => {
              restoreSiteLocation(analysis);
              setResultsOpen(false);
              try {
                sessionStorage.setItem('resultsOpen', '0');
              } catch {
                /* ignore */
              }
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
              analysis.research_depth !== 'pro_partial' &&
              analysis.research_depth !== 'ic' &&
              analysis.research_depth !== 'ic_full' &&
              String(analysis.depth_tier || '').toLowerCase() !== 'ic_full' &&
              String(analysis.depth_tier || '').toLowerCase() !== 'pro_local' &&
              String(analysis.depth_tier || '').toLowerCase() !== 'pro_light'
            }
            onUnlockDeeper={() => {
              try {
                // Only skip Checkout when THIS site still has an unused / same-site IC credit
                if (icReportPending) {
                  sessionStorage.setItem('icForceOnce', '1');
                  setPendingIcReport(true);
                } else if (entitlementTiers.some((t) => String(t).includes('ic'))) {
                  // Prior IC purchase exists but not for this site — force checkout path
                  sessionStorage.setItem('icForceOnce', '1');
                  setPendingIcReport(true);
                }
              } catch {
                /* ignore */
              }
              const restored = restoreSiteLocation(analysis);
              const incomplete =
                analysis.research_incomplete === true ||
                analysis.depth_claim_honest === false ||
                String(analysis.honesty?.source || '').toLowerCase() === 'instant';
              setResultsOpen(false);
              try {
                sessionStorage.setItem('resultsOpen', '0');
              } catch {
                /* ignore */
              }
              window.requestAnimationFrame(() => {
                document.getElementById('free-trial-form')?.scrollIntoView({
                  behavior: 'smooth',
                  block: 'start',
                });
              });
              if (incomplete && !restored.pin) {
                // Address restored; wait for LocationPicker forward-geocode to settle the pin
                pendingRerunAfterPinRef.current = true;
                setVoiceHint(
                  'Confirm the pin on the map for this address — deep research starts once it settles.'
                );
                return;
              }
              void runResearch();
            }}
            unlockLoading={loading}
            entitlementTiers={entitlementTiers}
            icReportPending={icReportPending}
          />
        </ErrorBoundary>
      )}
    </div>
  );
}
