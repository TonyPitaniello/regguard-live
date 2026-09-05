/**
 * Admin — product events / stamp funnel (zip-watch → re-run measure).
 */

import { useCallback, useEffect, useState } from 'react';
import { backendUrl } from './env';

function adminSecret(): string {
  try {
    return localStorage.getItem('rg_admin_secret') || '';
  } catch {
    return '';
  }
}

function setAdminSecret(value: string) {
  try {
    localStorage.setItem('rg_admin_secret', value);
  } catch {
    /* ignore */
  }
}

type FunnelRow = {
  ts?: string;
  event?: string;
  research_id?: string;
  zip?: string;
  stamp_grade?: string;
  channel?: string;
};

type Stats = {
  window_hours?: number;
  counts?: Record<string, number>;
  zip_watch_alerts?: number;
  reruns_same_zip?: number;
  rerun_within_72h?: number;
  rerun_within_72h_rate?: number | null;
  funnel?: {
    checkout_starts?: number;
    checkout_completes?: number;
    close_rate?: number | null;
    ic_project?: {
      views?: number;
      starts?: number;
      completes?: number;
      close_rate?: number | null;
      price_usd?: number;
    };
    contractor_pro_completes?: number;
  };
};

export function AdminStampFunnelDashboard() {
  const [secret, setSecret] = useState(adminSecret);
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<FunnelRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!secret.trim()) {
      setError('Enter ADMIN_SECRET to load stamp funnel');
      return;
    }
    setLoading(true);
    setError(null);
    setAdminSecret(secret.trim());
    try {
      const res = await fetch(
        `${backendUrl('/admin/stamp-funnel')}?hours=168`,
        { headers: { 'X-Admin-Secret': secret.trim() } }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStats(data.stats || null);
      setRecent(Array.isArray(data.recent) ? data.recent : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load stamp funnel');
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [secret]);

  useEffect(() => {
    if (secret.trim()) void load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- initial hydrate only

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-4">
      <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-end">
        <label className="flex-1 text-sm text-gray-300">
          Admin secret
          <input
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white"
            autoComplete="off"
          />
        </label>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold disabled:opacity-60"
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      {error && <p className="text-sm text-red-300">{error}</p>}
      {stats ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg border border-slate-700 p-3">
            <p className="text-xs text-gray-400">Zip-watch alerts</p>
            <p className="text-lg font-bold text-white">{stats.zip_watch_alerts ?? 0}</p>
          </div>
          <div className="rounded-lg border border-slate-700 p-3">
            <p className="text-xs text-gray-400">Same-ZIP re-runs</p>
            <p className="text-lg font-bold text-white">{stats.reruns_same_zip ?? 0}</p>
          </div>
          <div className="rounded-lg border border-slate-700 p-3">
            <p className="text-xs text-gray-400">Re-run within 72h</p>
            <p className="text-lg font-bold text-white">{stats.rerun_within_72h ?? 0}</p>
          </div>
          <div className="rounded-lg border border-slate-700 p-3">
            <p className="text-xs text-gray-400">72h conversion rate</p>
            <p className="text-lg font-bold text-white">
              {stats.rerun_within_72h_rate == null
                ? '—'
                : `${Math.round((stats.rerun_within_72h_rate || 0) * 100)}%`}
            </p>
          </div>
        </div>
      ) : null}
      {stats?.funnel ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg border border-cyan-700/50 p-3">
            <p className="text-xs text-gray-400">Checkout starts</p>
            <p className="text-lg font-bold text-white">{stats.funnel.checkout_starts ?? 0}</p>
          </div>
          <div className="rounded-lg border border-cyan-700/50 p-3">
            <p className="text-xs text-gray-400">Checkout completes</p>
            <p className="text-lg font-bold text-white">{stats.funnel.checkout_completes ?? 0}</p>
          </div>
          <div className="rounded-lg border border-cyan-700/50 p-3">
            <p className="text-xs text-gray-400">IC $1.5k close rate</p>
            <p className="text-lg font-bold text-white">
              {stats.funnel.ic_project?.close_rate == null
                ? '—'
                : `${Math.round((stats.funnel.ic_project.close_rate || 0) * 100)}%`}
            </p>
            <p className="text-[10px] text-gray-500">
              {stats.funnel.ic_project?.completes ?? 0}/{stats.funnel.ic_project?.starts || stats.funnel.ic_project?.views || 0}{' '}
              (starts→paid)
            </p>
          </div>
          <div className="rounded-lg border border-cyan-700/50 p-3">
            <p className="text-xs text-gray-400">Pro completes</p>
            <p className="text-lg font-bold text-white">
              {stats.funnel.contractor_pro_completes ?? 0}
            </p>
          </div>
        </div>
      ) : null}
      <p className="text-xs text-gray-400">
        Measure: zip-watch alerts → re-run within 72h (product_events + stamp_funnel_stats).
        Planning metrics only — not billing evidence.
      </p>
      <div className="overflow-x-auto rounded-xl border border-slate-700">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-900 text-left text-gray-400">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Event</th>
              <th className="px-3 py-2">ZIP</th>
              <th className="px-3 py-2">Grade</th>
              <th className="px-3 py-2">Research</th>
            </tr>
          </thead>
          <tbody>
            {recent.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-gray-500">
                  No recent events
                </td>
              </tr>
            ) : (
              recent.slice(0, 40).map((r, i) => (
                <tr key={`${r.ts || i}-${r.event || i}`} className="border-t border-slate-800">
                  <td className="px-3 py-2 text-gray-300">{r.ts || '—'}</td>
                  <td className="px-3 py-2 text-gray-200">{r.event || '—'}</td>
                  <td className="px-3 py-2 text-gray-300">{r.zip || '—'}</td>
                  <td className="px-3 py-2 text-gray-300">{r.stamp_grade || '—'}</td>
                  <td className="px-3 py-2 text-gray-500 font-mono text-xs">{(r.research_id || '').slice(0, 16)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
