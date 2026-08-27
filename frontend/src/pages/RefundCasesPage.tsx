/**
 * Public refund / guarantee case page — trust surface for money-back claim.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Loader2, Shield } from 'lucide-react';
import { backendUrl } from '../env';

type RefundCase = {
  id: string;
  title: string;
  status: string;
  promise: string;
  what_happened: string;
  resolution: string;
  proof_required?: string[];
};

type Payload = {
  updated?: string;
  disclaimer?: string;
  cases?: RefundCase[];
};

export default function RefundCasesPage() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(backendUrl('/refund-cases'));
        if (!res.ok) throw new Error(`Failed (${res.status})`);
        const json = (await res.json()) as Payload;
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-3xl mx-auto px-4 py-10 sm:px-6 space-y-8">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-emerald-300 hover:text-emerald-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Home
        </Link>
        <header className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-wide text-emerald-300 flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Guarantee
          </p>
          <h1 className="text-3xl font-black">Refund cases</h1>
          <p className="text-gray-300 text-sm">
            If a Critical fee or gotcha we labeled SOURCE is wrong against the official schedule on
            that date, we refund 100% of that paid run. Publish real cases here as they happen —
            templates stay until the first payout.
          </p>
          {data?.updated ? (
            <p className="text-xs text-gray-500">Updated {data.updated}</p>
          ) : null}
        </header>

        {error ? <p className="text-amber-300 text-sm">{error}</p> : null}
        {!data && !error ? (
          <div className="flex items-center gap-2 text-gray-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading…
          </div>
        ) : null}

        {data?.disclaimer ? (
          <p className="text-xs text-gray-500 border border-slate-800 rounded-lg p-3">
            {data.disclaimer}
          </p>
        ) : null}

        <div className="space-y-4">
          {(data?.cases || []).map((c) => (
            <article
              key={c.id}
              className="rounded-xl border border-slate-700 bg-slate-900/50 p-5 space-y-2"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-bold">{c.title}</h2>
                <span className="text-xs uppercase tracking-wide border border-slate-600 rounded px-2 py-0.5 text-gray-300">
                  {c.status}
                </span>
              </div>
              <p className="text-sm text-emerald-100/90">{c.promise}</p>
              <p className="text-sm text-gray-300">{c.what_happened}</p>
              <p className="text-sm text-gray-400">{c.resolution}</p>
              {(c.proof_required || []).length > 0 ? (
                <ul className="list-disc pl-5 text-xs text-gray-500 space-y-1">
                  {c.proof_required!.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
