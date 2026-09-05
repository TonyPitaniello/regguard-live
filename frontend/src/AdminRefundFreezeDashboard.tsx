/**
 * Admin — refund cases + freeze war-room stamps + create refund with stamp proof.
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

type CaseRow = {
  id?: string;
  title?: string;
  status?: string;
  research_id?: string;
  what_happened?: string;
  stamp_grade?: string;
  stamp_fingerprint?: string;
  stripe_refund_id?: string;
};

type FreezeRow = {
  research_id?: string;
  stamp_grade?: string;
  stamp_fingerprint?: string;
  stamp_frozen?: boolean;
  stamp_frozen_at?: string;
};

export function AdminRefundFreezeDashboard() {
  const [secret, setSecret] = useState(adminSecret);
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [freezeId, setFreezeId] = useState('');
  const [freezeResult, setFreezeResult] = useState<FreezeRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [freezeLoading, setFreezeLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createMsg, setCreateMsg] = useState('');
  const [form, setForm] = useState({
    title: '',
    research_id: '',
    what_happened: '',
    resolution: '',
    status: 'recorded',
    stripe_refund_id: '',
  });

  const load = useCallback(async () => {
    if (!secret.trim()) {
      setError('Enter ADMIN_SECRET to load refund cases');
      return;
    }
    setLoading(true);
    setError(null);
    setAdminSecret(secret.trim());
    try {
      const res = await fetch(backendUrl('/refund-cases'), {
        headers: { 'X-Admin-Secret': secret.trim() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCases(Array.isArray(data.cases) ? data.cases : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load refund cases');
    } finally {
      setLoading(false);
    }
  }, [secret]);

  const freeze = async () => {
    if (!freezeId.trim()) {
      setError('Enter research_id to freeze');
      return;
    }
    setFreezeLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${backendUrl(`/research/${encodeURIComponent(freezeId.trim())}/war-room/freeze`)}`,
        { method: 'POST' }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setFreezeResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Freeze failed');
    } finally {
      setFreezeLoading(false);
    }
  };

  const createCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!secret.trim()) {
      setError('Enter ADMIN_SECRET');
      return;
    }
    if (!form.title.trim()) {
      setError('Title required');
      return;
    }
    setCreating(true);
    setCreateMsg('');
    setError(null);
    setAdminSecret(secret.trim());
    try {
      const res = await fetch(backendUrl('/admin/refund-cases'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Secret': secret.trim(),
        },
        body: JSON.stringify({
          title: form.title.trim(),
          research_id: form.research_id.trim(),
          what_happened: form.what_happened.trim(),
          resolution: form.resolution.trim(),
          status: form.status.trim() || 'recorded',
          stripe_refund_id: form.stripe_refund_id.trim(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      const c = data.case || {};
      setCreateMsg(
        `Recorded ${c.id || 'case'} · grade ${c.stamp_grade || '—'} · fp ${(c.stamp_fingerprint || '').slice(0, 12) || '—'}`
      );
      setForm({
        title: '',
        research_id: form.research_id,
        what_happened: '',
        resolution: '',
        status: 'recorded',
        stripe_refund_id: '',
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setCreating(false);
    }
  };

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

      <form
        onSubmit={createCase}
        className="space-y-3 rounded-lg border border-slate-700 p-4 bg-slate-900/40"
      >
        <p className="text-sm font-bold text-white">Create refund case (with stamp proof)</p>
        <p className="text-xs text-gray-400">
          Attach <code className="text-amber-200">research_id</code> to freeze grade + fingerprint
          from the receipt. Stripe refund id optional.
        </p>
        <input
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white text-sm"
          placeholder="Title — e.g. Wrong Critical fee on Plano ZIP"
          value={form.title}
          onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          required
        />
        <input
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white text-sm"
          placeholder="research_id (required for stamp proof)"
          value={form.research_id}
          onChange={(e) => setForm((f) => ({ ...f, research_id: e.target.value }))}
        />
        <textarea
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white text-sm"
          placeholder="What happened"
          rows={3}
          value={form.what_happened}
          onChange={(e) => setForm((f) => ({ ...f, what_happened: e.target.value }))}
        />
        <textarea
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white text-sm"
          placeholder="Resolution"
          rows={2}
          value={form.resolution}
          onChange={(e) => setForm((f) => ({ ...f, resolution: e.target.value }))}
        />
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            className="flex-1 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white text-sm"
            placeholder="Status (recorded / refunded / denied)"
            value={form.status}
            onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
          />
          <input
            className="flex-1 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white text-sm"
            placeholder="Stripe refund id (optional)"
            value={form.stripe_refund_id}
            onChange={(e) => setForm((f) => ({ ...f, stripe_refund_id: e.target.value }))}
          />
        </div>
        <button
          type="submit"
          disabled={creating}
          className="px-4 py-2 rounded-lg bg-white text-slate-900 font-bold text-sm disabled:opacity-60"
        >
          {creating ? 'Recording…' : 'Record refund case'}
        </button>
        {createMsg ? <p className="text-xs text-emerald-300">{createMsg}</p> : null}
      </form>

      <div className="space-y-2 rounded-lg border border-slate-700 p-3">
        <p className="text-sm font-bold text-white">Freeze war-room stamp</p>
        <p className="text-xs text-gray-400">
          Locks stamp for dispute proof and blocks new war-room comments.
        </p>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            className="flex-1 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white text-sm"
            placeholder="research_id"
            value={freezeId}
            onChange={(e) => setFreezeId(e.target.value)}
          />
          <button
            type="button"
            onClick={() => void freeze()}
            disabled={freezeLoading}
            className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold disabled:opacity-60"
          >
            {freezeLoading ? 'Freezing…' : 'Freeze stamp'}
          </button>
        </div>
        {freezeResult ? (
          <p className="text-xs text-emerald-300">
            Frozen · grade {freezeResult.stamp_grade || '—'} · fp{' '}
            {(freezeResult.stamp_fingerprint || '').slice(0, 12)}
          </p>
        ) : null}
      </div>

      <h3 className="text-sm font-bold text-white">Refund cases ({cases.length})</h3>
      <div className="overflow-x-auto rounded-xl border border-slate-700">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-900 text-left text-gray-400">
            <tr>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Research</th>
              <th className="px-3 py-2">Grade / fp</th>
              <th className="px-3 py-2">Stripe</th>
            </tr>
          </thead>
          <tbody>
            {cases.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-gray-500">
                  No cases yet
                </td>
              </tr>
            ) : (
              cases.map((c, i) => (
                <tr key={c.id || i} className="border-t border-slate-800">
                  <td className="px-3 py-2 text-gray-200">{c.title || '—'}</td>
                  <td className="px-3 py-2 text-gray-300">{c.status || '—'}</td>
                  <td className="px-3 py-2 text-gray-400 font-mono text-xs">
                    {(c.research_id || '').slice(0, 16)}
                  </td>
                  <td className="px-3 py-2 text-gray-300 text-xs">
                    {c.stamp_grade || '—'} · {(c.stamp_fingerprint || '').slice(0, 10)}
                  </td>
                  <td className="px-3 py-2 text-gray-500 font-mono text-xs">
                    {(c.stripe_refund_id || '').slice(0, 14) || '—'}
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
