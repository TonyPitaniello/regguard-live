/**
 * GEO landing pages from DFW / Austin city packs → free lookup CTA.
 * Hub: /permit-fees  City: /{slug}-permit-fees
 */

import { useEffect, useMemo, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, ExternalLink } from 'lucide-react';
import { backendUrl } from '../env';
import { SeoHead } from '../SeoHead';
import {
  METRO_LANDINGS,
  isMetroPermitPath,
  metroFromPath,
  type MetroLanding,
} from '../metroCatalog';

type ApiMetro = MetroLanding & {
  portal_url?: string;
  fees_url?: string;
  ahj_name?: string;
  documents?: string[];
  fee_summary?: string[];
  cta_path?: string;
};

function runLookupPath(metro: MetroLanding, ctaPath?: string) {
  if (ctaPath) return ctaPath;
  return `/?city=${encodeURIComponent(metro.city)}&state=${encodeURIComponent(metro.state)}&utm_source=seo&utm_medium=organic&utm_campaign=metro_${metro.slug}&utm_content=permit-fees#free-trial-form`;
}

function MetroHub() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <SeoHead
        title="Texas metro permit fees — DFW & Austin Bid Risk Receipts | Reg Guard"
        description="Pre-bid permit diligence for Plano, Dallas, Austin, Fort Worth, Frisco and more. Forwardable Bid Risk Receipt — planning aid, not a quote."
        canonical="https://app.regguardagent.com/permit-fees"
      />
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 min-h-[44px]"
          >
            <ArrowLeft className="w-4 h-4" />
            RegGuard
          </button>
        </div>
      </header>
      <section className="px-4 py-14 max-w-3xl mx-auto">
        <p className="text-emerald-400 text-sm font-semibold mb-2">Passive beachhead · DFW / Austin</p>
        <h1 className="text-4xl font-black text-white mb-4">Permit fees &amp; bid-day gotchas by city</h1>
        <p className="text-lg text-gray-300 mb-8">
          Built for estimators and permit runners. Run an address, forward the Bid Risk Receipt.
          Planning aid — confirm with the AHJ before you bid.
        </p>
        <ul className="grid sm:grid-cols-2 gap-3">
          {METRO_LANDINGS.map((m) => (
            <li key={m.slug}>
              <Link
                to={`/${m.slug}-permit-fees`}
                className="block rounded-xl border border-purple-500/30 bg-slate-900/60 px-4 py-3 text-white hover:border-emerald-400/50"
              >
                <span className="font-bold">{m.city}, {m.state}</span>
                <span className="block text-sm text-gray-400 mt-0.5">Permit fees &amp; pre-bid gotchas</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default function GeoPermitLandingPage() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const local = useMemo(() => metroFromPath(pathname), [pathname]);
  const [api, setApi] = useState<ApiMetro | null>(null);

  useEffect(() => {
    if (!local) return;
    let cancelled = false;
    fetch(backendUrl(`/seo/metros/${encodeURIComponent(local.slug)}`))
      .then((r) => (r.ok ? r.json() : null))
      .then((row) => {
        if (!cancelled && row?.slug) {
          setApi({
            ...local,
            title: row.title || local.title,
            headline: row.headline || local.headline,
            bullets: row.bullets?.length ? row.bullets : local.bullets,
            feeNote: row.fee_note || local.feeNote,
            portal_url: row.portal_url,
            fees_url: row.fees_url,
            ahj_name: row.ahj_name,
            documents: row.documents,
            fee_summary: row.fee_summary,
            cta_path: row.cta_path,
          });
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [local]);

  if (pathname.replace(/\/$/, '') === '/permit-fees') {
    return <MetroHub />;
  }
  if (!isMetroPermitPath(pathname) || !local) {
    return <Navigate to="/" replace />;
  }

  const data = api || local;
  const canonical = `https://app.regguardagent.com/${local.slug}-permit-fees`;
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: data.title,
    description: data.headline,
    url: canonical,
    about: `${data.city} ${data.state} building and electrical permit diligence for contractors`,
    publisher: {
      '@type': 'Organization',
      name: 'Reg Guard · Pitaniello Perkins LLC',
      url: 'https://app.regguardagent.com/',
    },
  };

  const goRun = () => {
    navigate(runLookupPath(local, api?.cta_path));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <SeoHead title={`${data.title} | Reg Guard`} description={data.headline} canonical={canonical} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 min-h-[44px]"
          >
            <ArrowLeft className="w-4 h-4" />
            RegGuard
          </button>
          <Link to="/permit-fees" className="text-sm text-emerald-300 hover:text-white min-h-[44px] inline-flex items-center">
            All metros
          </Link>
        </div>
      </header>

      <section className="px-4 py-14 max-w-2xl mx-auto">
        <p className="text-emerald-400 text-sm font-semibold mb-2">DFW / Austin beachhead</p>
        <h1 className="text-4xl font-black text-white mb-4">{data.title}</h1>
        <p className="text-xl text-gray-300 mb-8">{data.headline}</p>

        <ul className="space-y-3 mb-8 text-gray-300">
          {data.bullets.map((b) => (
            <li key={b} className="flex gap-2">
              <span className="text-emerald-400">•</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>

        {api?.fee_summary && api.fee_summary.length > 0 ? (
          <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-50">
            {api.fee_summary.map((f) => (
              <p key={f} className="mb-1 last:mb-0">
                {f}
              </p>
            ))}
          </div>
        ) : null}

        <p className="text-gray-500 text-sm mb-6">{data.feeNote}</p>

        {api?.ahj_name ? (
          <p className="text-sm text-gray-400 mb-8">
            AHJ: {api.ahj_name}
            {api.portal_url ? (
              <>
                {' · '}
                <a href={api.portal_url} className="text-emerald-300 underline inline-flex items-center gap-1" target="_blank" rel="noreferrer">
                  Official portal <ExternalLink className="w-3 h-3" />
                </a>
              </>
            ) : null}
            {api.fees_url ? (
              <>
                {' · '}
                <a href={api.fees_url} className="text-emerald-300 underline" target="_blank" rel="noreferrer">
                  Fee schedule
                </a>
              </>
            ) : null}
          </p>
        ) : null}

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={goRun}
            className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold min-h-[44px]"
          >
            Run free {local.city} site lookup
          </button>
          {local.samplePdf && (
            <a
              href={backendUrl('/sample/plano-punch-list.pdf')}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-white/10 border border-purple-400/40 text-white font-semibold min-h-[44px]"
            >
              <Download className="w-4 h-4" />
              SAMPLE Plano PDF
            </a>
          )}
        </div>

        {api?.documents && api.documents.length > 0 ? (
          <div className="mt-10">
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-400 mb-2">Typical submittals (confirm with AHJ)</h2>
            <ul className="text-sm text-gray-300 list-disc pl-5 space-y-1">
              {api.documents.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    </div>
  );
}
