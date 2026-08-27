import { useCallback, useEffect, useState } from 'react';
import { backendUrl } from './env';

type Credit = {
  id?: string;
  ts?: string;
  status?: string;
  credit_usd?: number;
  email?: string;
  zip?: string;
  tier?: string;
  note_preview?: string;
};

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

export function AdminGotchaCreditsDashboard() {
  const [secret, setSecret] = useState(adminSecret);
  const [credits, setCredits] = useState<Credit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!secret.trim()) {
      setError('Enter ADMIN_SECRET');
      return;
    }
    setLoading(true);
    setError(null);
    setAdminSecret(secret.trim());
    try {
      const res = await fetch(backendUrl('/admin/gotcha-credits?limit=100'), {
        headers: { 'X-Admin-Secret': secret.trim() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCredits(Array.isArray(data.credits) ? data.credits : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
      setCredits([]);
    } finally {
      setLoading(false);
    }
  }, [secret]);

  useEffect(() => {
    if (secret.trim()) void load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const act = async (id: string, action: 'approve' | 'reject') => {
    if (!id || !secret.trim()) return;
    setBusy(id);
    try {
      const res = await fetch(
        backendUrl(`/admin/gotcha-credits/${encodeURIComponent(id)}/${action}?reviewer=ops`),
        { method: 'POST', headers: { 'X-Admin-Secret': secret.trim() } }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(null);
    }
  };

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
          />
        </label>
        <button
          type="button"
          onClick={() => void load()}
          className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold"
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      {error && <p className="text-sm text-red-300">{error}</p>}
      <p className="text-xs text-gray-400">
        Approve applies a $20 account credit used on next Partner/Pro checkout (price_data path).
      </p>
      <div className="overflow-x-auto rounded-xl border border-slate-700">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-900 text-left text-gray-400">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">ZIP</th>
              <th className="px-3 py-2">Note</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {credits.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-gray-500">
                  No credits yet
                </td>
              </tr>
            ) : (
              credits.map((c, i) => (
                <tr key={c.id || `${c.email}-${c.ts}-${i}`} className="border-t border-slate-800">
                  <td className="px-3 py-2 text-gray-300 whitespace-nowrap">{c.ts || '—'}</td>
                  <td className="px-3 py-2 text-amber-200">{c.status || '—'}</td>
                  <td className="px-3 py-2 text-gray-200">{c.email || '—'}</td>
                  <td className="px-3 py-2 text-gray-300">{c.zip || '—'}</td>
                  <td className="px-3 py-2 text-gray-400 max-w-xs truncate">{c.note_preview || ''}</td>
                  <td className="px-3 py-2 space-x-2 whitespace-nowrap">
                    {c.status === 'pending_review' && c.id && (
                      <>
                        <button
                          type="button"
                          disabled={busy === c.id}
                          onClick={() => void act(c.id!, 'approve')}
                          className="text-emerald-300 font-semibold underline"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          disabled={busy === c.id}
                          onClick={() => void act(c.id!, 'reject')}
                          className="text-red-300 font-semibold underline"
                        >
                          Reject
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
