/**
 * Admin — demand scoreboard (Blank question) + weekly pain-scout digest.
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

type DemandBoard = {
  verdict?: string;
  verdict_plain?: string;
  funnel?: Record<string, number>;
  rates?: Record<string, number | null>;
  top_zips?: Array<{
    zip: string;
    runs: number;
    receipts: number;
    shares: number;
    opens: number;
    share_rate?: number | null;
  }>;
  demand_feedback?: Record<string, number>;
};

type PainDigest = {
  generated_at?: string;
  verdict?: string;
  verdict_plain?: string;
  recommended_actions?: string[];
  market_pain_themes?: Array<{ id: string; theme: string; who: string; implication: string }>;
  weak_share_zips?: Array<{ zip: string; runs?: number; share_rate?: number | null }>;
  strong_share_zips?: Array<{ zip: string; shares?: number; share_rate?: number | null }>;
  blank_reminder?: string;
};

function pct(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—';
  return `${Math.round(v * 100)}%`;
}

export function AdminDemandDashboard() {
  const [secret, setSecret] = useState(adminSecret);
  const [demand, setDemand] = useState<DemandBoard | null>(null);
  const [digest, setDigest] = useState<PainDigest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(
    async (refreshDigest = false) => {
      if (!secret.trim()) {
        setError('Enter ADMIN_SECRET to load demand scoreboard');
        return;
      }
      setLoading(true);
      setError(null);
      setAdminSecret(secret.trim());
      try {
        const headers = { 'X-Admin-Secret': secret.trim() };
        const [boardRes, painRes] = await Promise.all([
          fetch(`${backendUrl('/admin/demand-scoreboard')}?hours=168`, { headers }),
          fetch(
            `${backendUrl('/admin/pain-scout')}?hours=168${refreshDigest ? '&refresh=true' : ''}`,
            { headers }
          ),
        ]);
        if (!boardRes.ok) throw new Error(`Scoreboard HTTP ${boardRes.status}`);
        if (!painRes.ok) throw new Error(`Pain scout HTTP ${painRes.status}`);
        const boardData = await boardRes.json();
        const painData = await painRes.json();
        setDemand(boardData.demand || null);
        setDigest(painData.digest || null);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load demand board');
        setDemand(null);
        setDigest(null);
      } finally {
        setLoading(false);
      }
    },
    [secret]
  );

  useEffect(() => {
    if (secret.trim()) void load(false);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const funnel = demand?.funnel || {};
  const rates = demand?.rates || {};

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-black text-white">Demand scoreboard</h1>
        <p className="text-sm text-gray-400 mt-1">
          Blank’s question, automated: do real contractors run → download → share → open → pay?
        </p>
      </div>

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
          onClick={() => void load(false)}
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold disabled:opacity-60"
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
        <button
          type="button"
          onClick={() => void load(true)}
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-white/10 border border-emerald-400/40 text-emerald-100 font-semibold disabled:opacity-60"
        >
          Rebuild pain-scout
        </button>
      </div>

      {error && <p className="text-sm text-red-300">{error}</p>}

      {demand ? (
        <div className="rounded-xl border border-emerald-500/35 bg-emerald-500/10 p-4 space-y-2">
          <p className="text-xs font-bold uppercase tracking-wide text-emerald-300">
            Verdict · {demand.verdict || '—'}
          </p>
          <p className="text-white font-semibold">{demand.verdict_plain}</p>
        </div>
      ) : null}

      {demand ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            ['Runs', funnel.research_runs],
            ['Receipts', funnel.receipt_downloads],
            ['Shares', funnel.shares],
            ['/r/ opens', funnel.shared_report_opens],
            ['Returns', funnel.returns_or_saves],
            ['Paid', funnel.checkout_completes],
          ].map(([label, val]) => (
            <div key={String(label)} className="rounded-lg border border-slate-700 p-3">
              <p className="text-xs text-gray-400">{label}</p>
              <p className="text-lg font-bold text-white">{val ?? 0}</p>
            </div>
          ))}
        </div>
      ) : null}

      {demand ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg border border-cyan-700/50 p-3">
            <p className="text-xs text-gray-400">Receipt / run</p>
            <p className="text-lg font-bold text-white">{pct(rates.receipt_per_run)}</p>
          </div>
          <div className="rounded-lg border border-cyan-700/50 p-3">
            <p className="text-xs text-gray-400">Share / receipt</p>
            <p className="text-lg font-bold text-white">{pct(rates.share_per_receipt)}</p>
          </div>
          <div className="rounded-lg border border-cyan-700/50 p-3">
            <p className="text-xs text-gray-400">Open / share</p>
            <p className="text-lg font-bold text-white">{pct(rates.open_per_share)}</p>
          </div>
          <div className="rounded-lg border border-cyan-700/50 p-3">
            <p className="text-xs text-gray-400">Pay / run</p>
            <p className="text-lg font-bold text-white">{pct(rates.pay_per_run)}</p>
          </div>
        </div>
      ) : null}

      {demand?.top_zips && demand.top_zips.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-900 text-left text-gray-400">
              <tr>
                <th className="px-3 py-2">ZIP</th>
                <th className="px-3 py-2">Runs</th>
                <th className="px-3 py-2">Receipts</th>
                <th className="px-3 py-2">Shares</th>
                <th className="px-3 py-2">Opens</th>
                <th className="px-3 py-2">Share rate</th>
              </tr>
            </thead>
            <tbody>
              {demand.top_zips.map((z) => (
                <tr key={z.zip} className="border-t border-slate-800">
                  <td className="px-3 py-2 text-white font-mono">{z.zip}</td>
                  <td className="px-3 py-2 text-gray-300">{z.runs}</td>
                  <td className="px-3 py-2 text-gray-300">{z.receipts}</td>
                  <td className="px-3 py-2 text-gray-300">{z.shares}</td>
                  <td className="px-3 py-2 text-gray-300">{z.opens}</td>
                  <td className="px-3 py-2 text-emerald-200">{pct(z.share_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {digest ? (
        <section className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-bold text-white">Weekly pain-scout digest</h2>
            <p className="text-xs text-gray-400">{digest.generated_at || '—'}</p>
          </div>
          <p className="text-sm text-amber-100">{digest.verdict_plain}</p>
          <ul className="list-disc pl-5 space-y-1 text-sm text-gray-200">
            {(digest.recommended_actions || []).map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
          <div className="space-y-2 pt-2 border-t border-amber-500/20">
            <p className="text-xs font-bold uppercase tracking-wide text-amber-200">Market themes</p>
            {(digest.market_pain_themes || []).map((t) => (
              <div key={t.id} className="text-sm text-gray-300">
                <span className="text-white font-medium">{t.theme}</span>
                <span className="text-gray-500"> · {t.who}</span>
                <p className="text-xs text-gray-400 mt-0.5">{t.implication}</p>
              </div>
            ))}
          </div>
          {digest.blank_reminder ? (
            <p className="text-xs text-gray-500 pt-2">{digest.blank_reminder}</p>
          ) : null}
        </section>
      ) : null}

      <p className="text-xs text-gray-500">
        Also see{' '}
        <a className="text-emerald-300 underline" href="/admin/stamp-funnel">
          /admin/stamp-funnel
        </a>
        . Cron: <code className="text-gray-400">POST /cron/weekly-pain-scout</code> with{' '}
        <code className="text-gray-400">X-Cron-Secret</code>.
      </p>
    </div>
  );
}
