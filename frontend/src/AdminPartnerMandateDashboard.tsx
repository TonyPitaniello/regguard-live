/**
 * Admin — partner mandate kit + outreach log.
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

type Outreach = {
  id?: string;
  ts?: string;
  partner_name?: string;
  partner_email?: string;
  metro?: string;
  note?: string;
  status?: string;
};

type Kit = {
  one_liner?: string;
  script?: string;
  templates?: Record<string, string>;
  day0?: string;
  day7?: string;
};

export function AdminPartnerMandateDashboard() {
  const [secret, setSecret] = useState(adminSecret);
  const [kit, setKit] = useState<Kit | null>(null);
  const [outreach, setOutreach] = useState<Outreach[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!secret.trim()) {
      setError('Enter ADMIN_SECRET to load partner mandate');
      return;
    }
    setLoading(true);
    setError(null);
    setAdminSecret(secret.trim());
    try {
      const res = await fetch(backendUrl('/admin/partner-mandate'), {
        headers: { 'X-Admin-Secret': secret.trim() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setKit(data.kit || null);
      setOutreach(Array.isArray(data.outreach) ? data.outreach : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load partner mandate');
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
      {kit ? (
        <div className="space-y-3">
          {kit.one_liner ? (
            <p className="text-sm text-emerald-300 border border-emerald-500/30 rounded-lg p-3">
              {kit.one_liner}
            </p>
          ) : null}
          {kit.day0 ? (
            <div className="rounded-lg border border-slate-700 p-3">
              <p className="text-xs uppercase text-gray-400 mb-1">Day-0</p>
              <p className="text-sm text-gray-200 whitespace-pre-wrap">{kit.day0}</p>
            </div>
          ) : null}
          {kit.day7 ? (
            <div className="rounded-lg border border-slate-700 p-3">
              <p className="text-xs uppercase text-gray-400 mb-1">Day-7</p>
              <p className="text-sm text-gray-200 whitespace-pre-wrap">{kit.day7}</p>
            </div>
          ) : null}
          {kit.templates ? (
            <div className="space-y-2">
              <p className="text-xs text-gray-400">Templates</p>
              {Object.entries(kit.templates).map(([k, v]) => (
                <pre
                  key={k}
                  className="text-xs text-gray-300 bg-black/40 border border-white/10 rounded-lg p-3 overflow-auto max-h-48 whitespace-pre-wrap"
                >
                  {v}
                </pre>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      <h3 className="text-sm font-bold text-white">Outreach log ({outreach.length})</h3>
      <div className="overflow-x-auto rounded-xl border border-slate-700">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-900 text-left text-gray-400">
            <tr>
              <th className="px-3 py-2">When</th>
              <th className="px-3 py-2">Partner</th>
              <th className="px-3 py-2">Metro</th>
              <th className="px-3 py-2">Note</th>
            </tr>
          </thead>
          <tbody>
            {outreach.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-center text-gray-500">
                  No outreach logged
                </td>
              </tr>
            ) : (
              outreach.map((o, i) => (
                <tr key={o.id || i} className="border-t border-slate-800">
                  <td className="px-3 py-2 text-gray-300">{o.ts || '—'}</td>
                  <td className="px-3 py-2 text-gray-200">{o.partner_name || '—'}</td>
                  <td className="px-3 py-2 text-gray-300">{o.metro || '—'}</td>
                  <td className="px-3 py-2 text-gray-400">{(o.note || '').slice(0, 120)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
