/**
 * Human-readable moratorium / pause radar (not raw JSON).
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, RefreshCw } from 'lucide-react';
import { backendUrl } from '../env';

type Metro = {
  metro?: string;
  state?: string;
  status?: string;
  summary?: string;
};

type RadarPayload = {
  updated?: string;
  disclaimer?: string;
  metros?: Metro[];
  bill_notes?: string[];
};

function statusClass(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('high')) return 'bg-red-500/20 text-red-200 border-red-500/40';
  if (s.includes('watch')) return 'bg-amber-500/20 text-amber-100 border-amber-500/40';
  if (s.includes('active') || s.includes('build')) return 'bg-emerald-500/20 text-emerald-100 border-emerald-500/40';
  return 'bg-slate-500/20 text-slate-200 border-slate-500/40';
}

export default function MoratoriumRadarPage() {
  const [data, setData] = useState<RadarPayload | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(backendUrl('/dc/moratorium-radar'));
      if (!res.ok) throw new Error(`Radar unavailable (${res.status})`);
      const json = (await res.json()) as RadarPayload;
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load radar');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 text-white">
      <div className="max-w-3xl mx-auto px-4 py-8 sm:py-12">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-emerald-300 hover:text-emerald-200 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Reg Guard
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight">Moratorium radar</h1>
            <p className="text-slate-300 text-sm mt-2 max-w-xl">
              Seeded planning watchlist for large-load / pause politics — not a live legislative API.
              Verify ordinance and bill status with counsel before bid.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-600 bg-slate-900/60 text-sm font-semibold hover:bg-slate-800"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {loading && !data ? (
          <p className="text-slate-400">Loading radar…</p>
        ) : null}

        {error ? (
          <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 flex gap-3">
            <AlertTriangle className="w-5 h-5 text-red-300 shrink-0" />
            <div>
              <p className="font-bold text-red-100">Could not load radar</p>
              <p className="text-sm text-red-200/90 mt-1">{error}</p>
            </div>
          </div>
        ) : null}

        {data ? (
          <div className="space-y-4">
            {data.updated ? (
              <p className="text-xs text-slate-400">Updated: {data.updated}</p>
            ) : null}
            {data.disclaimer ? (
              <p className="text-sm text-amber-100/90 border border-amber-500/30 bg-amber-500/10 rounded-lg p-3">
                {data.disclaimer}
              </p>
            ) : null}

            <ul className="space-y-3">
              {(data.metros || []).map((m) => {
                const key = `${m.metro || ''}-${m.state || ''}-${m.status || ''}`;
                const status = String(m.status || 'watch');
                return (
                  <li
                    key={key}
                    className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <h2 className="font-bold text-white text-base">
                        {m.metro || 'Metro'}
                        {m.state ? `, ${m.state}` : ''}
                      </h2>
                      <span
                        className={`text-[11px] font-bold uppercase tracking-wide px-2 py-0.5 rounded border ${statusClass(status)}`}
                      >
                        {status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 leading-relaxed">{m.summary}</p>
                  </li>
                );
              })}
            </ul>

            {(data.bill_notes || []).length > 0 ? (
              <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
                <h3 className="text-sm font-bold text-emerald-300 mb-2">Bill / session notes</h3>
                <ul className="space-y-2">
                  {(data.bill_notes || []).map((n) => (
                    <li key={n} className="text-sm text-slate-300">
                      • {n}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
