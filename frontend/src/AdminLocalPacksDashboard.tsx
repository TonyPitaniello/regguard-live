import { useCallback, useEffect, useState } from 'react';
import { backendUrl } from './env';

type DraftRow = {
  zip: string;
  city?: string;
  state?: string;
  hits?: number;
  tier?: string;
  fee_count?: number;
  gotcha_count?: number;
  portal_url?: string;
  promote_candidate?: boolean;
  readiness?: number;
};

type PacksResponse = {
  drafts?: DraftRow[];
  demand?: Array<{ zip: string; hits?: number; city?: string; state?: string }>;
  promoted?: Array<{ ahj_id?: string; city?: string; state?: string; portal_url?: string }>;
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

export function AdminLocalPacksDashboard() {
  const [secret, setSecret] = useState(adminSecret);
  const [data, setData] = useState<PacksResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyZip, setBusyZip] = useState<string | null>(null);
  const [seedNote, setSeedNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!secret.trim()) {
      setError('Enter ADMIN_SECRET to load packs');
      return;
    }
    setLoading(true);
    setError(null);
    setAdminSecret(secret.trim());
    try {
      const res = await fetch(backendUrl('/admin/local-packs?min_hits=1&limit=50'), {
        headers: { 'X-Admin-Secret': secret.trim() },
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load packs');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [secret]);

  useEffect(() => {
    if (secret.trim()) {
      void load();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- initial hydrate only

  const promote = async (zip: string) => {
    if (!secret.trim() || !zip) return;
    const reviewer = window.prompt('Reviewer name', 'ops') || 'ops';
    setBusyZip(zip);
    setError(null);
    try {
      const res = await fetch(backendUrl(`/admin/local-packs/${encodeURIComponent(zip)}/promote`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Secret': secret.trim(),
        },
        body: JSON.stringify({ reviewer }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.detail || `Promote failed HTTP ${res.status}`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Promote failed');
    } finally {
      setBusyZip(null);
    }
  };

  const seed = async () => {
    if (!secret.trim()) return;
    setSeedNote(null);
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(backendUrl('/admin/local-packs/seed'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Secret': secret.trim(),
        },
        body: JSON.stringify({ limit: 5, max_pages: 4 }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.detail || `Seed failed HTTP ${res.status}`);
      }
      setSeedNote(`Seeded ${body.seeded ?? 0} ZIP(s)`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Seed failed');
    } finally {
      setLoading(false);
    }
  };

  const drafts = data?.drafts || [];
  const promoted = data?.promoted || [];
  const demand = data?.demand || [];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>Local packs</h1>
      <p style={{ color: '#64748b', marginBottom: 20 }}>
        Ops queue for draft ZIP packs — promote only after portal + fee/gotcha + citation look right.
      </p>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        <input
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder="ADMIN_SECRET"
          style={{
            flex: '1 1 220px',
            padding: '8px 12px',
            border: '1px solid #cbd5e1',
            borderRadius: 6,
          }}
        />
        <button type="button" onClick={() => void load()} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
        <button type="button" onClick={() => void seed()} disabled={loading || !secret.trim()}>
          Seed top ZIPs
        </button>
      </div>

      {error && (
        <p style={{ color: '#b91c1c', marginBottom: 12 }} role="alert">
          {error}
        </p>
      )}
      {seedNote && (
        <p style={{ color: '#15803d', marginBottom: 12 }}>{seedNote}</p>
      )}

      <h2 style={{ fontSize: 18, fontWeight: 600, marginTop: 24 }}>Drafts ({drafts.length})</h2>
      <div style={{ overflowX: 'auto', marginTop: 8 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
              <th style={{ padding: 8 }}>ZIP</th>
              <th style={{ padding: 8 }}>City</th>
              <th style={{ padding: 8 }}>Hits</th>
              <th style={{ padding: 8 }}>Tier</th>
              <th style={{ padding: 8 }}>Fees</th>
              <th style={{ padding: 8 }}>Gotchas</th>
              <th style={{ padding: 8 }}>Ready</th>
              <th style={{ padding: 8 }}>Portal</th>
              <th style={{ padding: 8 }} />
            </tr>
          </thead>
          <tbody>
            {drafts.map((d) => (
              <tr key={d.zip} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ padding: 8, fontFamily: 'ui-monospace, monospace' }}>{d.zip}</td>
                <td style={{ padding: 8 }}>
                  {[d.city, d.state].filter(Boolean).join(', ') || '—'}
                </td>
                <td style={{ padding: 8 }}>{d.hits ?? 0}</td>
                <td style={{ padding: 8 }}>{d.tier || '—'}</td>
                <td style={{ padding: 8 }}>{d.fee_count ?? 0}</td>
                <td style={{ padding: 8 }}>{d.gotcha_count ?? 0}</td>
                <td style={{ padding: 8 }}>
                  {d.promote_candidate ? '✓' : '·'}{' '}
                  {typeof d.readiness === 'number' ? d.readiness.toFixed(2) : ''}
                </td>
                <td style={{ padding: 8, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {d.portal_url ? (
                    <a href={d.portal_url} target="_blank" rel="noreferrer">
                      link
                    </a>
                  ) : (
                    '—'
                  )}
                </td>
                <td style={{ padding: 8 }}>
                  <button
                    type="button"
                    disabled={busyZip === d.zip || !d.promote_candidate}
                    onClick={() => void promote(d.zip)}
                    title={d.promote_candidate ? 'Promote to library' : 'Not a promote candidate yet'}
                  >
                    {busyZip === d.zip ? '…' : 'Promote'}
                  </button>
                </td>
              </tr>
            ))}
            {!drafts.length && !loading && (
              <tr>
                <td colSpan={9} style={{ padding: 16, color: '#64748b' }}>
                  No drafts yet — run seed or wait for paid local confirms.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h2 style={{ fontSize: 18, fontWeight: 600, marginTop: 32 }}>
        Demand ({demand.length})
      </h2>
      <ul style={{ fontSize: 14, color: '#334155', lineHeight: 1.6 }}>
        {demand.slice(0, 15).map((r) => (
          <li key={r.zip}>
            <code>{r.zip}</code> — {r.hits ?? 0} hits
            {r.city ? ` · ${r.city}, ${r.state || ''}` : ''}
          </li>
        ))}
      </ul>

      <h2 style={{ fontSize: 18, fontWeight: 600, marginTop: 32 }}>
        Promoted ({promoted.length})
      </h2>
      <ul style={{ fontSize: 14, color: '#334155', lineHeight: 1.6 }}>
        {promoted.map((p) => (
          <li key={p.ahj_id || `${p.city}-${p.state}`}>
            <strong>{p.ahj_id}</strong> — {p.city}, {p.state}{' '}
            {p.portal_url ? (
              <a href={p.portal_url} target="_blank" rel="noreferrer">
                portal
              </a>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
