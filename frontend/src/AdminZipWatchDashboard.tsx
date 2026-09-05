/**
 * Admin — zip-watch health + stale re-run measure.
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

export function AdminZipWatchDashboard() {
  const [secret, setSecret] = useState(adminSecret);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!secret.trim()) {
      setError('Enter ADMIN_SECRET to load zip-watch');
      return;
    }
    setLoading(true);
    setError(null);
    setAdminSecret(secret.trim());
    try {
      const res = await fetch(backendUrl('/admin/zip-watch'), {
        headers: { 'X-Admin-Secret': secret.trim() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setHealth(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load zip-watch');
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
      {health ? (
        <div className="rounded-xl border border-slate-700 p-4 space-y-2 text-sm text-gray-200">
          <p className="text-xs text-gray-400">Zip-watch health</p>
          <pre className="text-xs overflow-auto max-h-72 bg-black/40 border border-white/10 rounded-lg p-3">
            {JSON.stringify(health, null, 2)}
          </pre>
        </div>
      ) : null}
      <p className="text-xs text-gray-400">
        Stale packs are flagged by fingerprint change. Use stamp funnel for
        zip-watch → re-run within 72h conversion.
      </p>
    </div>
  );
}
