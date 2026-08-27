import { useCallback, useEffect, useState } from 'react';
import { backendUrl } from './env';

type SmsEvent = {
  ts?: string;
  event?: string;
  message_sid?: string;
  status?: string;
  error_code?: string | number | null;
  to?: string;
  from?: string;
  research_id?: string;
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

export function AdminSmsDeliveryDashboard() {
  const [secret, setSecret] = useState(adminSecret);
  const [events, setEvents] = useState<SmsEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!secret.trim()) {
      setError('Enter ADMIN_SECRET to load SMS delivery');
      return;
    }
    setLoading(true);
    setError(null);
    setAdminSecret(secret.trim());
    try {
      const res = await fetch(backendUrl('/admin/sms-delivery?limit=100'), {
        headers: { 'X-Admin-Secret': secret.trim() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setEvents(Array.isArray(data.events) ? data.events : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load SMS events');
      setEvents([]);
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
      <p className="text-xs text-gray-400">
        Twilio status callbacks → <code className="text-amber-200">/webhooks/twilio/sms-status</code>
        . Delivered / failed / undelivered show here after sends.
      </p>
      <div className="overflow-x-auto rounded-xl border border-slate-700">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-900 text-left text-gray-400">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Event</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">To</th>
              <th className="px-3 py-2">SID</th>
              <th className="px-3 py-2">Err</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-gray-500">
                  No SMS events yet
                </td>
              </tr>
            ) : (
              events.map((ev, i) => (
                <tr key={`${ev.message_sid || i}-${ev.ts || i}`} className="border-t border-slate-800">
                  <td className="px-3 py-2 text-gray-300 whitespace-nowrap">{ev.ts || '—'}</td>
                  <td className="px-3 py-2 text-gray-200">{ev.event || '—'}</td>
                  <td className="px-3 py-2">
                    <span
                      className={
                        ev.status === 'delivered'
                          ? 'text-emerald-300 font-semibold'
                          : ev.status === 'failed' || ev.status === 'undelivered'
                            ? 'text-red-300 font-semibold'
                            : 'text-amber-200'
                      }
                    >
                      {ev.status || '—'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-gray-300">{ev.to || '—'}</td>
                  <td className="px-3 py-2 text-gray-500 font-mono text-xs">
                    {(ev.message_sid || '').slice(0, 18) || '—'}
                  </td>
                  <td className="px-3 py-2 text-red-300">{ev.error_code ?? ''}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
