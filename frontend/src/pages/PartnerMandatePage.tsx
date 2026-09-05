/**
 * Partner mandate page — full kit (script, templates, day0/day7, outreach log).
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Copy, Check } from 'lucide-react';
import { backendUrl } from '../env';

type Kit = {
  one_liner?: string;
  script?: string;
  templates?: Record<string, string>;
  day0?: string;
  day7?: string;
  talking_points?: string[];
  success_signal?: string;
  disclaimer?: string;
};

export default function PartnerMandatePage() {
  const navigate = useNavigate();
  const [kit, setKit] = useState<Kit | null>(null);
  const [copied, setCopied] = useState(false);
  const [partnerName, setPartnerName] = useState('');
  const [partnerEmail, setPartnerEmail] = useState('');
  const [metro, setMetro] = useState('DFW');
  const [note, setNote] = useState('');
  const [receiptId, setReceiptId] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(backendUrl('/partner/mandate'));
        const data = await res.json();
        if (!cancelled) setKit(data);
      } catch {
        if (!cancelled) setError('Could not load mandate kit');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const copyScript = async () => {
    const text = [kit?.one_liner, kit?.script].filter(Boolean).join('\n\n');
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
    try {
      await fetch(backendUrl('/events'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: 'partner_mandate_copy', channel: 'mandate_page' }),
      });
    } catch {
      /* ignore */
    }
  };

  const logOutreach = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg('');
    setError('');
    try {
      const res = await fetch(backendUrl('/partner/mandate/outreach'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          partner_name: partnerName.trim(),
          partner_email: partnerEmail.trim(),
          metro: metro.trim(),
          note: note.trim(),
          receipt_research_id: receiptId.trim(),
          logged_by: sessionStorage.getItem('userEmail') || '',
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Log failed');
      setMsg(`Logged outreach to ${partnerName}. Forward one real receipt this week.`);
      setPartnerName('');
      setNote('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Log failed');
    }
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
        <h1 className="text-3xl font-black tracking-tight">Partner mandate</h1>
        <p className="text-gray-400 text-sm">
          Make the RegGuard stamp required in bid week: “no stamp, no bid attach.”
        </p>
        {kit?.one_liner ? (
          <p className="text-lg font-semibold text-emerald-300 border border-emerald-500/30 rounded-lg p-4">
            {kit.one_liner}
          </p>
        ) : null}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void copyScript()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 font-bold text-sm"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? 'Copied' : 'Copy script'}
          </button>
        </div>
        {kit?.script ? (
          <pre className="whitespace-pre-wrap text-xs text-gray-300 bg-black/40 border border-white/10 rounded-lg p-4 overflow-auto max-h-80">
            {kit.script}
          </pre>
        ) : null}
        {kit?.day0 || kit?.day7 ? (
          <div className="space-y-3">
            {kit.day0 ? (
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm">
                <p className="text-xs uppercase text-emerald-400/80 mb-1">Day-0</p>
                <p className="whitespace-pre-wrap">{kit.day0}</p>
              </div>
            ) : null}
            {kit.day7 ? (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
                <p className="text-xs uppercase text-amber-300/80 mb-1">Day-7</p>
                <p className="whitespace-pre-wrap">{kit.day7}</p>
              </div>
            ) : null}
          </div>
        ) : null}
        {kit?.templates ? (
          <div className="space-y-3">
            <p className="text-xs uppercase text-gray-400">Templates</p>
            {Object.entries(kit.templates).map(([k, v]) => (
              <div key={k} className="space-y-1">
                <p className="text-sm font-semibold text-emerald-300">{k}</p>
                <pre className="whitespace-pre-wrap text-xs text-gray-300 bg-black/40 border border-white/10 rounded-lg p-3 overflow-auto max-h-48">
                  {v}
                </pre>
              </div>
            ))}
          </div>
        ) : null}
        {kit?.talking_points?.length ? (
          <ul className="space-y-2 text-sm text-gray-300 list-disc pl-5">
            {kit.talking_points.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        ) : null}
        {kit?.disclaimer ? <p className="text-xs text-gray-500">{kit.disclaimer}</p> : null}

        <form onSubmit={logOutreach} className="space-y-3 border border-white/10 rounded-xl p-4">
          <p className="text-sm font-bold uppercase tracking-wide text-gray-400">
            Log outreach (5–10 partners)
          </p>
          <input
            className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm"
            placeholder="Partner name"
            value={partnerName}
            onChange={(e) => setPartnerName(e.target.value)}
            required
          />
          <input
            className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm"
            placeholder="Email (optional)"
            value={partnerEmail}
            onChange={(e) => setPartnerEmail(e.target.value)}
          />
          <input
            className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm"
            placeholder="Metro (DFW / Austin)"
            value={metro}
            onChange={(e) => setMetro(e.target.value)}
          />
          <input
            className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm"
            placeholder="Receipt research id (optional)"
            value={receiptId}
            onChange={(e) => setReceiptId(e.target.value)}
          />
          <textarea
            className="w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm"
            placeholder="Note — e.g. sent script + one receipt"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
          />
          <button type="submit" className="px-4 py-2 rounded-lg bg-white text-slate-900 font-bold text-sm">
            Log outreach
          </button>
          {msg ? <p className="text-sm text-emerald-300">{msg}</p> : null}
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
        </form>
      </div>
    </div>
  );
}
