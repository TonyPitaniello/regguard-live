/**
 * Affiliate / referral signup — get a ?ref= link, track unpaid commissions via API.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Copy, Check } from 'lucide-react';
import { backendUrl } from '../env';

export default function AffiliatePage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [referralUrl, setReferralUrl] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const register = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(backendUrl('/affiliates/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          name: name.trim(),
          code: code.trim() || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Registration failed');
      setReferralUrl(data.referral_url || '');
      if (data.affiliate?.code) {
        sessionStorage.setItem('affiliateCode', data.affiliate.code);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    if (!referralUrl) return;
    await navigator.clipboard.writeText(referralUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 transition min-h-[44px]"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        </div>
      </header>

      <section className="px-4 py-14 max-w-xl mx-auto">
        <h1 className="text-4xl font-black text-white mb-3">Affiliate referrals</h1>
        <p className="text-gray-300 mb-8">
          Share Reg Guard. Earn 20% of each referred customer&apos;s <strong>first</strong> paid
          checkout (Partner, Pro, or IC) — not recurring renewals. Forward Bid Risk Receipts with your
          link for <strong>$10 account credit</strong> per unique receipt. Payouts are marked paid
          manually — email support@regguardagent.com when ready. After signup, open your{' '}
          <a href="/partner/portal" className="text-emerald-400 underline">
            Partner portal
          </a>
          .
        </p>

        {!referralUrl ? (
          <form onSubmit={register} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg bg-slate-800 border border-purple-500/30 px-4 py-3 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name (optional)</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg bg-slate-800 border border-purple-500/30 px-4 py-3 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Custom code (optional)</label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. dallas-mike"
                className="w-full rounded-lg bg-slate-800 border border-purple-500/30 px-4 py-3 text-white"
              />
            </div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold disabled:opacity-50 min-h-[44px]"
            >
              {loading ? 'Creating…' : 'Get my referral link'}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-emerald-400 font-semibold">Your link is ready</p>
            <div className="flex gap-2">
              <input
                readOnly
                value={referralUrl}
                className="flex-1 rounded-lg bg-slate-800 border border-purple-500/30 px-4 py-3 text-white text-sm"
              />
              <button
                type="button"
                onClick={copy}
                className="px-4 rounded-lg bg-white/10 text-white border border-purple-400/40 min-h-[44px]"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-gray-400 text-sm">
              Anyone who lands with your <code className="text-purple-300">?ref=</code> and later
              pays is attributed to you at checkout.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
