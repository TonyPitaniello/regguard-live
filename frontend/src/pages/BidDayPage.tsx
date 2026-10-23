/**
 * Bid-day list — several addresses, one HOLD or CLEAR per row.
 * Free screens the first row. Estimator screens the list. No counsel ZIP on this desk.
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { backendUrl } from '../env';
import { parseBidDayLines, type BidDayLine } from '../bidDayParse';
import { getJobsEmail, getOwnerKey, persistSavedJob, setJobsEmail } from '../jobsOwner';

const PAID_CAP = 8;

type Desk = 'free' | 'partner' | 'pro';

type RowResult = {
  status: 'idle' | 'queued' | 'running' | 'ready' | 'held' | 'error';
  stamp: string;
  risk: string;
  pct: string;
  fee: string;
  share: string;
  note: string;
};

const EMPTY: RowResult = {
  status: 'idle',
  stamp: '',
  risk: '',
  pct: '',
  fee: '',
  share: '',
  note: '',
};

function stampWord(raw: string): string {
  const g = raw.toUpperCase();
  if (g === 'FAIL' || g === 'HOLD') return 'HOLD';
  if (g === 'PASS' || g === 'CLEAR') return 'CLEAR';
  if (g === 'CAUTION') return 'CAUTION';
  return g;
}

function stampClass(stamp: string): string {
  if (stamp === 'HOLD') return 'bg-amber-500/15 text-amber-200 border-amber-400/40';
  if (stamp === 'CLEAR') return 'bg-emerald-500/15 text-emerald-200 border-emerald-400/40';
  if (stamp === 'CAUTION') return 'bg-amber-500/10 text-amber-100 border-amber-300/30';
  return 'bg-slate-800 text-slate-300 border-slate-600';
}

function readAnalysis(payload: Record<string, unknown>) {
  const analysis = (payload.analysis_data || {}) as Record<string, unknown>;
  const stamp = (analysis.regguard_stamp || {}) as { grade?: string };
  const grade = stampWord(String(stamp.grade || analysis.stamp_grade || ''));
  const killers = Array.isArray(analysis.margin_killers)
    ? (analysis.margin_killers as { title?: string }[])
    : [];
  const band = (analysis.contingency_band || {}) as {
    pct_low?: number;
    pct_high?: number;
  };
  const depth = String(analysis.research_depth || payload.research_depth || '').toLowerCase();
  const fees = ((analysis.fee_card || {}) as { fees?: { label?: string; amount_usd?: number }[] }).fees || [];
  const firstFee = fees.find((fee) => typeof fee.amount_usd === 'number');
  const share =
    String(payload.share_url || analysis.share_url || '').trim() ||
    (analysis.research_id ? `https://app.regguardagent.com/r/${analysis.research_id}` : '');
  const researchId = String(payload.research_id || analysis.research_id || '');
  return { grade, risk: String(killers[0]?.title || '').trim(), band, depth, firstFee, share, researchId };
}

function rowText(line: BidDayLine, row: RowResult): string {
  const place = [line.address, line.city, line.state, line.zip].filter(Boolean).join(', ');
  return [
    row.stamp ? `${row.stamp} — ${place}` : place,
    row.risk ? `Top risk: ${row.risk}` : '',
    row.pct ? `Contingency: ${row.pct}` : 'Clear percent stays on Estimator.',
    row.share || 'https://app.regguardagent.com',
  ]
    .filter(Boolean)
    .join('\n');
}

export default function BidDayPage() {
  const [email, setEmail] = useState(getJobsEmail);
  const [projectType, setProjectType] = useState('commercial');
  const [paste, setPaste] = useState('');
  const [lines, setLines] = useState<BidDayLine[]>([]);
  const [rows, setRows] = useState<RowResult[]>([]);
  const [desk, setDesk] = useState<Desk>('free');
  const [running, setRunning] = useState(false);
  const [banner, setBanner] = useState('');

  const readyCount = useMemo(() => lines.filter((line) => !line.error).length, [lines]);

  const readList = () => {
    const parsed = parseBidDayLines(paste);
    setLines(parsed);
    setRows(
      parsed.map((line) =>
        line.error ? { ...EMPTY, status: 'error', note: line.error } : { ...EMPTY }
      )
    );
    setBanner(
      parsed.length === 0
        ? 'Paste at least one line: street, city, ST ZIP.'
        : ''
    );
  };

  const screen = async () => {
    const emailNorm = email.trim().toLowerCase();
    if (!emailNorm || !emailNorm.includes('@')) {
      setBanner('Email is required. The list is saved to that address.');
      return;
    }
    const parsed = parseBidDayLines(paste);
    setLines(parsed);
    if (!parsed.some((line) => !line.error)) {
      setBanner('No readable address. Use street, city, ST ZIP on each line.');
      return;
    }
    setJobsEmail(emailNorm);
    setRunning(true);
    setBanner('');

    let nextDesk: Desk = 'free';
    try {
      const res = await fetch(`${backendUrl('/entitlement')}?email=${encodeURIComponent(emailNorm)}`);
      const data = await res.json().catch(() => ({}));
      if (data.deep_research || data.pro_research) nextDesk = 'pro';
      else if (data.habit_access || data.paid) nextDesk = 'partner';
    } catch {
      nextDesk = 'free';
    }
    setDesk(nextDesk);

    const cap = nextDesk === 'free' ? 1 : PAID_CAP;
    const mode = nextDesk === 'pro' ? 'pro' : nextDesk === 'partner' ? 'partner' : 'free';
    const nextRows = parsed.map(() => ({ ...EMPTY, status: 'queued' as const }));
    let runnable = 0;
    parsed.forEach((line, index) => {
      if (line.error) {
        nextRows[index] = { ...EMPTY, status: 'error', note: line.error };
        return;
      }
      runnable += 1;
      if (runnable > cap) {
        nextRows[index] = {
          ...EMPTY,
          status: 'held',
          note:
            nextDesk === 'free'
              ? 'Estimator screens the rest of the list.'
              : `Bid day screens ${PAID_CAP} addresses at a time.`,
        };
      }
    });
    setRows(nextRows);

    let ran = 0;
    for (let index = 0; index < parsed.length; index += 1) {
      const line = parsed[index];
      if (line.error || nextRows[index].status === 'held') continue;
      if (ran >= cap) continue;
      ran += 1;
      setRows((prev) => prev.map((row, i) => (i === index ? { ...row, status: 'running' } : row)));
      try {
        const response = await fetch(backendUrl('/free-trial'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            address: line.address,
            city: line.city,
            state: line.state,
            zip: line.zip,
            project_type: projectType,
            email: emailNorm,
            owner_key: getOwnerKey() || undefined,
            research_mode: mode,
            generate_ic_report: false,
          }),
        });
        const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
        if (response.status === 429) {
          const detail =
            typeof payload.detail === 'string'
              ? payload.detail
              : 'Free monthly lookups are used up. Estimator screens the list.';
          setRows((prev) =>
            prev.map((row, i) =>
              i === index ? { ...EMPTY, status: 'held', note: detail } : row.status === 'queued' ? { ...EMPTY, status: 'held', note: 'Stopped. Estimator screens the rest.' } : row
            )
          );
          setBanner(detail);
          break;
        }
        if (!response.ok || !payload.analysis_data) {
          const detail = typeof payload.detail === 'string' ? payload.detail : 'No screening came back.';
          setRows((prev) => prev.map((row, i) => (i === index ? { ...EMPTY, status: 'error', note: detail } : row)));
          continue;
        }
        const read = readAnalysis(payload);
        const frosted = nextDesk === 'free' || read.depth === 'free' || read.depth === 'preview';
        const pct =
          frosted || read.band.pct_low == null || read.band.pct_high == null
            ? ''
            : `+${read.band.pct_low}% – +${read.band.pct_high}%`;
        const fee =
          nextDesk === 'pro' && read.firstFee && typeof read.firstFee.amount_usd === 'number'
            ? `${read.firstFee.label || 'Fee'} · $${read.firstFee.amount_usd.toLocaleString()}`
            : '';
        const result: RowResult = {
          status: 'ready',
          stamp: read.grade || '—',
          risk: read.risk || 'Confirm the punch with the city.',
          pct,
          fee,
          share: read.share,
          note: '',
        };
        setRows((prev) => prev.map((row, i) => (i === index ? result : row)));
        void persistSavedJob({
          owner_email: emailNorm,
          address: line.address,
          city: line.city,
          state: line.state,
          zip: line.zip,
          project_type: projectType,
          last_research_id: read.researchId,
          share_url: read.share,
          last_stamp_grade: read.grade,
          preview: frosted,
        });
      } catch {
        setRows((prev) =>
          prev.map((row, i) =>
            i === index ? { ...EMPTY, status: 'error', note: 'The screening did not finish.' } : row
          )
        );
      }
    }
    setRunning(false);
  };

  const copyText = async (line: BidDayLine, row: RowResult) => {
    const body = rowText(line, row);
    try {
      await navigator.clipboard.writeText(body);
      setBanner('Text copied. Paste it into the bid thread.');
    } catch {
      setBanner(body);
    }
  };

  const copyThread = async () => {
    const blocks = lines
      .map((line, index) => ({ line, row: rows[index] || EMPTY }))
      .filter((item) => !item.line.error && item.row.status === 'ready')
      .map((item) => rowText(item.line, item.row));
    if (!blocks.length) {
      setBanner('Screen the list first. The thread is one HOLD or CLEAR per address.');
      return;
    }
    const body = [...blocks, 'Run your own address: https://app.regguardagent.com'].join('\n\n');
    try {
      await navigator.clipboard.writeText(body);
      setBanner('Thread copied. Paste it where the bid is being discussed.');
    } catch {
      setBanner(body);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b1220] text-white">
      <header className="border-b border-white/10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-4">
          <Link to="/" className="text-sm font-semibold tracking-wide text-slate-300 hover:text-white">
            Reg Guard
          </Link>
          <Link to="/jobs" className="text-sm text-slate-400 hover:text-white">
            Saved Jobs
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-300/90">Bid day</p>
        <h1 className="mt-2 text-3xl sm:text-4xl font-semibold tracking-tight text-white">
          Screen the list before the number goes out
        </h1>
        <p className="mt-3 max-w-2xl text-sm sm:text-base leading-relaxed text-slate-300">
          One HOLD or CLEAR per address, with the top risk and a link the GC can open. Free screens
          the first row. Estimator screens the list and unlocks the clear percent. Contractor Pro adds
          the fee line on rows you are bidding. This desk is not a counsel ZIP and not an interconnection
          study.
        </p>

        <section className="mt-8 grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Addresses</span>
            <textarea
              value={paste}
              onChange={(event) => setPaste(event.target.value)}
              rows={8}
              spellCheck={false}
              placeholder={'9999 Chapin School Road, Fort Worth, TX 76126\n500 Congress Ave, Austin, TX 78701'}
              className="mt-2 w-full rounded-md border border-white/10 bg-[#121a2b] px-3 py-3 font-mono text-sm leading-6 text-slate-100 placeholder:text-slate-500 focus:border-emerald-400/60 focus:outline-none"
            />
          </label>
          <div className="flex flex-col gap-4">
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                className="mt-2 w-full rounded-md border border-white/10 bg-[#121a2b] px-3 py-3 text-sm text-white focus:border-emerald-400/60 focus:outline-none"
              />
            </label>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Project type</span>
              <select
                value={projectType}
                onChange={(event) => setProjectType(event.target.value)}
                className="mt-2 w-full rounded-md border border-white/10 bg-[#121a2b] px-3 py-3 text-sm text-white focus:border-emerald-400/60 focus:outline-none"
              >
                <option value="commercial">Commercial building</option>
                <option value="industrial">Industrial</option>
                <option value="data-center">Data center / large load</option>
                <option value="utility">Utility / substation</option>
                <option value="renewable">Solar / wind / battery</option>
                <option value="other">Other</option>
              </select>
            </label>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={readList}
                disabled={running}
                className="min-h-[44px] rounded-md border border-white/15 px-4 text-sm font-semibold text-slate-100 hover:bg-white/5 disabled:opacity-50"
              >
                Read the list
              </button>
              <button
                type="button"
                onClick={() => void screen()}
                disabled={running}
                className="inline-flex min-h-[44px] items-center gap-2 rounded-md bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                {running ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {running ? 'Screening…' : 'Screen the list'}
              </button>
              <button
                type="button"
                onClick={() => void copyThread()}
                disabled={running || !rows.some((row) => row.status === 'ready')}
                className="min-h-[44px] rounded-md border border-emerald-400/40 px-4 text-sm font-semibold text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-50"
              >
                Copy the thread
              </button>
            </div>
            <p className="text-xs leading-5 text-slate-500">
              {readyCount > 0 ? `${readyCount} readable ${readyCount === 1 ? 'address' : 'addresses'}. ` : ''}
              One line each: street, city, ST ZIP. Planning aid, not a quote.
            </p>
          </div>
        </section>

        {banner ? (
          <p className="mt-6 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200">
            {banner}
          </p>
        ) : null}

        {lines.length > 0 ? (
          <section className="mt-8 overflow-hidden rounded-md border border-white/10">
            <div className="hidden md:grid md:grid-cols-[minmax(0,1.4fr)_92px_minmax(0,1.2fr)_140px_minmax(0,0.8fr)_88px] gap-3 border-b border-white/10 bg-white/[0.03] px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              <span>Address</span>
              <span>Stamp</span>
              <span>Top risk</span>
              <span>Clear %</span>
              <span>{desk === 'pro' ? 'Fee line' : 'Desk'}</span>
              <span>Text</span>
            </div>
            <ul>
              {lines.map((line, index) => {
                const row = rows[index] || EMPTY;
                const place = line.error
                  ? line.raw
                  : `${line.address}, ${line.city}, ${line.state} ${line.zip}`;
                return (
                  <li
                    key={`${line.raw}-${index}`}
                    className="grid gap-2 border-b border-white/10 px-4 py-4 last:border-b-0 md:grid-cols-[minmax(0,1.4fr)_92px_minmax(0,1.2fr)_140px_minmax(0,0.8fr)_88px] md:items-center md:gap-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-white">{place}</p>
                      {row.note ? <p className="mt-1 text-xs text-slate-400">{row.note}</p> : null}
                    </div>
                    <div>
                      {row.status === 'running' ? (
                        <span className="text-xs text-slate-400">Screening</span>
                      ) : row.stamp ? (
                        <span className={`inline-flex rounded border px-2 py-0.5 text-xs font-semibold tracking-wide ${stampClass(row.stamp)}`}>
                          {row.stamp}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-500">{row.status === 'held' ? 'Held' : '—'}</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-300">{row.risk || '—'}</p>
                    <p className="text-sm tabular-nums text-slate-200">
                      {row.status === 'ready' && !row.pct ? (
                        <span className="text-slate-400">+••.•%</span>
                      ) : (
                        row.pct || '—'
                      )}
                    </p>
                    <p className="text-xs text-slate-400">
                      {row.fee ||
                        (desk === 'pro'
                          ? row.status === 'ready'
                            ? 'Confirm on the city schedule'
                            : '—'
                          : row.status === 'held' && desk === 'free'
                            ? 'Estimator'
                            : '—')}
                    </p>
                    <div>
                      {row.status === 'ready' ? (
                        <button
                          type="button"
                          onClick={() => void copyText(line, row)}
                          className="text-sm font-semibold text-emerald-300 hover:text-emerald-200"
                        >
                          Copy
                        </button>
                      ) : row.status === 'held' && desk === 'free' ? (
                        <Link to="/checkout/partner" className="text-sm font-semibold text-emerald-300 hover:text-emerald-200">
                          $79
                        </Link>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        ) : null}

        {desk === 'free' && lines.length > 1 ? (
          <p className="mt-4 text-sm text-slate-400">
            The rest of the list stays on{' '}
            <Link to="/checkout/partner" className="font-semibold text-emerald-300 hover:text-emerald-200">
              Estimator / Permit Runner — $79/mo
            </Link>
            . Forwarding a row does not unlock the clear percent.
          </p>
        ) : null}
      </main>
    </div>
  );
}
