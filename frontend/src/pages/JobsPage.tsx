/**
 * Saved Jobs list — email lookup against GET /jobs
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { backendUrl } from '../env';

type Job = {
  id: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  share_url?: string;
  updated_at?: string;
  last_run_at?: string;
  status?: string;
  stamp_stale?: boolean;
  last_stamp_grade?: string;
};

export default function JobsPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState(
    () => (typeof window !== 'undefined' && sessionStorage.getItem('userEmail')) || ''
  );
  const [phone, setPhone] = useState(
    () => (typeof window !== 'undefined' && sessionStorage.getItem('userPhone')) || ''
  );
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [recheckId, setRecheckId] = useState('');
  const [recheckMsg, setRecheckMsg] = useState('');

  const load = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setLoading(true);
    setError('');
    try {
      const emailNorm = email.trim().toLowerCase();
      sessionStorage.setItem('userEmail', emailNorm);
      if (phone.trim()) sessionStorage.setItem('userPhone', phone.trim());
      const res = await fetch(
        `${backendUrl('/jobs')}?email=${encodeURIComponent(emailNorm)}`
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Could not load jobs');
      setJobs(data.jobs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Load failed');
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 min-h-[44px]"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        </div>
      </header>

      <section className="px-4 py-12 max-w-2xl mx-auto">
        <h1 className="text-3xl font-black text-white mb-2">Saved Jobs</h1>
        <p className="text-gray-400 text-sm mb-6">
          Sites auto-save when you run a lookup. Weekly reminder emails use this list.
          Add a mobile on save (from results) so stamp-outdated SMS can reach you when Twilio is live.
          If a job shows STALE, re-check before bid (Day-7 preferred for LOI).
        </p>

        <form onSubmit={load} className="flex flex-col sm:flex-row gap-3 mb-8">
          <input
            type="email"
            required
            value={email}
            onChange={(ev) => setEmail(ev.target.value)}
            placeholder="your@email.com"
            className="flex-1 rounded-lg bg-slate-800 border border-purple-500/30 px-4 py-3 text-white"
          />
          <input
            type="tel"
            value={phone}
            onChange={(ev) => setPhone(ev.target.value)}
            placeholder="Mobile for stamp SMS (optional)"
            className="flex-1 rounded-lg bg-slate-800 border border-purple-500/30 px-4 py-3 text-white"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold disabled:opacity-50 min-h-[44px]"
          >
            {loading ? 'Loading…' : 'Load jobs'}
          </button>
        </form>

        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

        {recheckMsg && <p className="text-emerald-300 text-sm mb-4">{recheckMsg}</p>}

        <ul className="space-y-3">
          {jobs.map((j) => (
            <li
              key={j.id}
              className="border border-purple-500/20 rounded-xl px-4 py-3 bg-slate-800/40"
            >
              <p className="text-white font-semibold">{j.address || 'Site'}</p>
              <p className="text-gray-400 text-sm">
                {[j.city, j.state, j.zip].filter(Boolean).join(', ')}
              </p>
              {j.last_run_at && (
                <p className="text-gray-500 text-xs mt-1">Last run: {j.last_run_at}</p>
              )}
              {(j.stamp_stale || j.status === 'stale') && (
                <p className="text-xs text-amber-300 mt-1 border border-amber-500/40 rounded px-2 py-1">
                  STALE — re-run before bid (zip-watch / pack fingerprint changed).
                </p>
              )}
              <div className="flex flex-wrap gap-3 mt-2">
                {j.share_url && (
                  <a
                    href={j.share_url}
                    className="text-purple-300 text-sm hover:text-white"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open share link
                  </a>
                )}
                <button
                  type="button"
                  disabled={recheckId === j.id}
                  className="text-emerald-300 text-sm font-semibold hover:text-white disabled:opacity-50"
                  onClick={async () => {
                    const emailNorm = email.trim().toLowerCase();
                    setRecheckId(j.id);
                    setRecheckMsg('');
                    try {
                      const res = await fetch(backendUrl(`/jobs/${j.id}/recheck`), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ owner_email: emailNorm }),
                      });
                      const data = await res.json().catch(() => ({}));
                      if (!res.ok) throw new Error(data.detail || 'Recheck failed');
                      const n = data.diff?.change_count ?? 0;
                      setRecheckMsg(
                        n
                          ? `${j.address}: ${n} change(s) since last run`
                          : `${j.address}: recheck complete — no material changes`
                      );
                      sessionStorage.setItem('lastJobId', j.id);
                      await load();
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Recheck failed');
                    } finally {
                      setRecheckId('');
                    }
                  }}
                >
                  {recheckId === j.id ? 'Re-checking…' : 'Re-check before bid'}
                </button>
              </div>
            </li>
          ))}
          {!loading && jobs.length === 0 && !error && (
            <li className="text-gray-500 text-sm">No jobs yet — run a free lookup first.</li>
          )}
        </ul>
      </section>
    </div>
  );
}
