/**
 * GEO landing pages: Plano / Dallas / Austin permit fee → free lookup CTA
 */

import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download } from 'lucide-react';
import { backendUrl } from '../env';

type CityKey = 'plano' | 'dallas' | 'austin';

const CITY: Record<
  CityKey,
  { title: string; headline: string; bullets: string[]; feeNote: string }
> = {
  plano: {
    title: 'Plano TX electrical permit fees',
    headline: 'Pre-bid punch list for Plano AHJ work',
    bullets: [
      'Plano Ord. 250.50 grounding gotchas (dual 8-ft rods @ 20 ft, 2/0 bond) called out when citeable',
      '2026 electrical permit fee sync noted as $75 total — confirm on City of Plano schedule',
      'Every line shows a Source link or Unverified — forward only what you can defend',
    ],
    feeNote:
      'Fee figures are planning aids. Always confirm with City of Plano Building Inspections before bid or filing.',
  },
  dallas: {
    title: 'Dallas TX trade permit checklist',
    headline: 'Pre-bid diligence for Dallas commercial / industrial bids',
    bullets: [
      'Screen AHJ risks before you price the job',
      'Citeable punch list for Dallas-area sites when sources exist',
      'Share to unlock the full free preview — upgrade for deep scout research',
    ],
    feeNote:
      'Dallas fees and amendments change. Confirm with the City of Dallas permit office before filing.',
  },
  austin: {
    title: 'Austin TX AHJ permit checklist',
    headline: 'Pre-bid punch list for Austin Design Criteria risks',
    bullets: [
      'Austin gas-relief clearance and service-upgrade patterns when citeable',
      'Source or Unverified on every punch line',
      'IC Project Report adds memo + punch + permit worksheet PDFs (not official filings)',
    ],
    feeNote:
      'Austin Development Services fees and Design Criteria override generic NEC narratives — verify before bid.',
  },
};

function resolveCity(pathname: string): CityKey {
  const p = (pathname || '').toLowerCase();
  if (p.includes('dallas')) return 'dallas';
  if (p.includes('austin')) return 'austin';
  return 'plano';
}

export default function GeoPermitLandingPage() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const city = resolveCity(pathname);
  const data = CITY[city];

  const scrollToHome = () => {
    navigate('/');
    window.setTimeout(() => {
      document.getElementById('free-trial-form')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }, 120);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 min-h-[44px]"
          >
            <ArrowLeft className="w-4 h-4" />
            RegGuard
          </button>
          <nav className="flex gap-3 text-sm">
            {(['plano', 'dallas', 'austin'] as CityKey[]).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => navigate(`/${c}-permit-fees`)}
                className={
                  c === city
                    ? 'text-white font-semibold capitalize min-h-[44px]'
                    : 'text-purple-300 hover:text-white capitalize min-h-[44px]'
                }
              >
                {c}
              </button>
            ))}
          </nav>
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

        <p className="text-gray-500 text-sm mb-8">{data.feeNote}</p>

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={scrollToHome}
            className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold min-h-[44px]"
          >
            Run free {city} site lookup
          </button>
          {city === 'plano' && (
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
      </section>
    </div>
  );
}
