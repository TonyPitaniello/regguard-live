/**
 * Partner portal — mandate kit + referral link + credits + forward rewards.
 * Email lookup (same pattern as Saved Jobs).
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Copy, Check } from 'lucide-react';
import { backendUrl } from '../env';

type PortalPayload = {
  email?: string;
  kit?: {
    one_liner?: string;
    day0?: string;
    day7?: string;
    disclaimer?: string;
  };
  affiliate?: { code?: string; name?: string } | null;
  referral_url?: string;
  commissions?: Array<{
    id?: string;
    tier?: string;
    commission_cents?: number;
    paid?: boolean;
    created_at?: string;
  }>;
  unpaid_cents?: number;
  account_credit_usd?: number;
  forward_rewards?: {
    partner_total_usd?: number;
    forwarder_total_usd?: number;
    as_partner?: Array<{ research_id?: string; amount_usd?: number; ts?: string }>;
  };
  funnel_hint?: {
    pitch?: string;
    forward_credit_usd?: number;
    partner_forward_credit_usd?: number;
    ic_project_price_usd?: number;
  };
};

export default function PartnerPortalPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState(
    () => (typeof window !== 'undefined' && sessionStorage.getItem('userEmail')) || ''
  );
  const [data, setData] = useState<PortalPayload | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setLoading(true);
    setError('');
    try {
      const emailNorm = email.trim().toLowerCase();
      sessionStorage.setItem('userEmail', emailNorm);
      const res = await fetch(
        `${backendUrl('/partner/portal')}?email=${encodeURIComponent(emailNorm)}`
      );
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(json.detail || 'Could not load portal');
      setData(json);
      if (json.affiliate?.code) {
        sessionStorage.setItem('affiliateCode', json.affiliate.code);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Load failed');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const copyLink = async () => {
    if (!data?.referral_url) return;
    await navigator.clipboard.writeText(data.referral_url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-sm text-emerald-300"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <h1 className="text-3xl font-black tracking-tight">Partner portal</h1>
        <p className="text-gray-400 text-sm">
          Mandate kit, referral link, forward credits, and unpaid commissions — managed by email.
        </p>

        <form onSubmit={load} className="flex flex-col sm:flex-row gap-2">
          <input
            type="email"
            required
            value={email}
            onChange={(ev) => setEmail(ev.target.value)}
            placeholder="partner@email.com"
            className="flex-1 rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-emerald-600 font-bold text-sm disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Open portal'}
          </button>
        </form>
        {error ? <p className="text-sm text-red-300">{error}</p> : null}

        {data ? (
          <div className="space-y-5">
            {data.kit?.one_liner ? (
              <p className="text-emerald-300 border border-emerald-500/30 rounded-lg p-4 font-semibold">
                {data.kit.one_liner}
              </p>
            ) : null}

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-slate-700 p-3">
                <p className="text-xs text-gray-400">Account credit</p>
                <p className="text-xl font-bold">${(data.account_credit_usd ?? 0).toFixed(2)}</p>
              </div>
              <div className="rounded-lg border border-slate-700 p-3">
                <p className="text-xs text-gray-400">Unpaid commission</p>
                <p className="text-xl font-bold">
                  ${((data.unpaid_cents ?? 0) / 100).toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg border border-slate-700 p-3">
                <p className="text-xs text-gray-400">Partner forward credits</p>
                <p className="text-xl font-bold">
                  ${(data.forward_rewards?.partner_total_usd ?? 0).toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg border border-slate-700 p-3">
                <p className="text-xs text-gray-400">Your forward credits</p>
                <p className="text-xl font-bold">
                  ${(data.forward_rewards?.forwarder_total_usd ?? 0).toFixed(2)}
                </p>
              </div>
            </div>

            {data.funnel_hint?.pitch ? (
              <p className="text-sm text-gray-300 border border-white/10 rounded-lg p-3">
                {data.funnel_hint.pitch}
              </p>
            ) : null}

            {data.affiliate ? (
              <div className="space-y-2">
                <p className="text-sm font-bold text-white">
                  Referral code: <span className="text-emerald-300">{data.affiliate.code}</span>
                </p>
                <div className="flex gap-2">
                  <input
                    readOnly
                    value={data.referral_url || ''}
                    className="flex-1 rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-xs text-gray-300"
                  />
                  <button
                    type="button"
                    onClick={() => void copyLink()}
                    className="inline-flex items-center gap-1 px-3 py-2 rounded-lg bg-white text-slate-900 font-bold text-sm"
                  >
                    {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    Copy
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-amber-200">
                No affiliate yet —{' '}
                <Link to="/affiliate" className="underline text-emerald-300">
                  register a referral code
                </Link>{' '}
                to earn 20% of first paid checkout + $10 per unique receipt forward.
              </p>
            )}

            {(data.kit?.day0 || data.kit?.day7) && (
              <div className="space-y-2 text-sm">
                {data.kit.day0 ? (
                  <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
                    <p className="text-xs uppercase text-emerald-400 mb-1">Day-0</p>
                    <p className="whitespace-pre-wrap">{data.kit.day0}</p>
                  </div>
                ) : null}
                {data.kit.day7 ? (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
                    <p className="text-xs uppercase text-amber-300 mb-1">Day-7</p>
                    <p className="whitespace-pre-wrap">{data.kit.day7}</p>
                  </div>
                ) : null}
              </div>
            )}

            <div className="flex flex-wrap gap-3 text-sm">
              <Link to="/partner/mandate" className="text-emerald-300 underline">
                Full mandate kit
              </Link>
              <Link to="/affiliate" className="text-emerald-300 underline">
                Affiliate signup
              </Link>
              <Link to="/pricing" className="text-emerald-300 underline">
                Pricing (IC $1,500)
              </Link>
            </div>

            {(data.commissions || []).length > 0 ? (
              <div>
                <p className="text-sm font-bold mb-2">Recent commissions</p>
                <ul className="space-y-1 text-xs text-gray-400">
                  {data.commissions!.slice(0, 8).map((c) => (
                    <li key={c.id}>
                      {c.tier} · ${((c.commission_cents || 0) / 100).toFixed(2)} ·{' '}
                      {c.paid ? 'paid' : 'unpaid'} · {(c.created_at || '').slice(0, 10)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {data.kit?.disclaimer ? (
              <p className="text-xs text-gray-500">{data.kit.disclaimer}</p>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
