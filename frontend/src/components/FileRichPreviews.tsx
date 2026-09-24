/**
 * Rich in-app previews for IC Diligence Bundle members:
 * DOCX (mammoth HTML), XLSX/CSV (SheetJS → document tables).
 */

import { useEffect, useState } from 'react';
import mammoth from 'mammoth';
import * as XLSX from 'xlsx';

function humanTitle(filename: string): string {
  const base = (filename || '').split('/').pop() || filename || 'Document';
  return base
    .replace(/\.(docx|xlsx|xls|csv)$/i, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

type SheetPreview = {
  name: string;
  /** Banner / address lines above the table (Cover or sheet titles) */
  intro: string[];
  headers: string[];
  body: string[][];
  /** Two-column cover / summary layout */
  isCover: boolean;
};

const HEADER_HINT =
  /\b(trade|owner|exhibit|priority|item|fee|source|section|row.?type|claim|label|detail|status|due|qty|unit|site|kind|title|verified|notes|timeline)\b/i;

function nonEmptyCells(row: string[]): string[] {
  return row.map((c) => String(c ?? '').trim()).filter(Boolean);
}

/** Find the real column-header row under title / address banners. */
function findHeaderRowIndex(rows: string[][]): number {
  let bestIdx = 0;
  let bestScore = -1;
  const limit = Math.min(rows.length, 15);
  for (let i = 0; i < limit; i++) {
    const cells = nonEmptyCells(rows[i] || []);
    if (cells.length < 3) continue;
    const avgLen = cells.reduce((s, c) => s + c.length, 0) / cells.length;
    let score = cells.length * 12;
    if (avgLen > 48) score -= 25;
    if (cells.every((c) => c.length < 36)) score += 18;
    if (HEADER_HINT.test(cells.join(' '))) score += 60;
    // Title banners are usually one long cell in col 0
    if (cells.length === 1) score -= 40;
    if (score > bestScore) {
      bestScore = score;
      bestIdx = i;
    }
  }
  return bestScore >= 0 ? bestIdx : 0;
}

function normalizeRows(raw: unknown[][]): string[][] {
  return raw.map((r) =>
    (Array.isArray(r) ? r : []).map((c) => String(c ?? '').trim())
  );
}

function trimTrailingEmptyCols(rows: string[][]): string[][] {
  let max = 0;
  for (const row of rows) {
    for (let i = row.length - 1; i >= 0; i--) {
      if (row[i]) {
        max = Math.max(max, i + 1);
        break;
      }
    }
  }
  if (max <= 0) return rows;
  return rows.map((r) => {
    const next = r.slice(0, max);
    while (next.length < max) next.push('');
    return next;
  });
}

function buildSheetPreview(name: string, rawRows: string[][]): SheetPreview {
  const rows = trimTrailingEmptyCols(normalizeRows(rawRows)).filter((r) =>
    r.some((c) => c.trim())
  );
  const isCover =
    /^cover$/i.test(name) ||
    (rows[0] && nonEmptyCells(rows[0]).length <= 2 && findHeaderRowIndex(rows) === 0 && nonEmptyCells(rows[0]).length < 3);

  // Cover / summary: two-column key-value when most rows are pairs
  const pairish =
    rows.filter((r) => nonEmptyCells(r).length >= 1 && nonEmptyCells(r).length <= 2).length >=
    Math.max(3, Math.floor(rows.length * 0.6));

  if (isCover || (pairish && nonEmptyCells(rows[0] || []).length <= 2 && !HEADER_HINT.test((rows[0] || []).join(' ')))) {
    const body = rows
      .map((r) => {
        const cells = nonEmptyCells(r);
        if (cells.length === 0) return null;
        if (cells.length === 1) return ['', cells[0]];
        return [cells[0], cells.slice(1).join(' — ')];
      })
      .filter(Boolean) as string[][];
    return {
      name,
      intro: [],
      headers: ['Field', 'Value'],
      body,
      isCover: true,
    };
  }

  const headerIdx = findHeaderRowIndex(rows);
  const intro = rows
    .slice(0, headerIdx)
    .map((r) => nonEmptyCells(r).join(' — '))
    .filter(Boolean);
  let headers = (rows[headerIdx] || []).map((c) => c.trim());
  // Drop trailing empties from header
  while (headers.length && !headers[headers.length - 1]) headers.pop();
  if (!headers.length) headers = ['Value'];
  const colCount = headers.length;
  const body = rows.slice(headerIdx + 1).map((r) => {
    const next = r.slice(0, colCount);
    while (next.length < colCount) next.push('');
    return next;
  });

  return { name, intro, headers, body, isCover: false };
}

function workbookToSheets(wb: XLSX.WorkBook): SheetPreview[] {
  const sheets = wb.SheetNames.map((name) => {
    const sheet = wb.Sheets[name];
    const rows = XLSX.utils.sheet_to_json<string[]>(sheet, {
      header: 1,
      defval: '',
      raw: false,
      blankrows: false,
    }) as string[][];
    return buildSheetPreview(name, rows);
  }).filter((s) => s.body.length > 0 || s.intro.length > 0 || s.headers.length > 0);

  // Prefer data sheets first in the tab strip (Cover last)
  sheets.sort((a, b) => Number(a.isCover) - Number(b.isCover));
  return sheets;
}

function defaultActiveIndex(sheets: SheetPreview[]): number {
  const i = sheets.findIndex((s) => !s.isCover);
  return i >= 0 ? i : 0;
}

function SheetDocument({
  title,
  sheets,
  active,
  onSelect,
}: {
  title: string;
  sheets: SheetPreview[];
  active: number;
  onSelect: (i: number) => void;
}) {
  const sheet = sheets[active] || sheets[0];
  if (!sheet) {
    return (
      <p className="text-gray-500 text-sm p-6">This workbook has no readable rows.</p>
    );
  }
  const { headers, body, intro, isCover } = sheet;

  return (
    <div className="min-h-full bg-[#e8edf5] px-3 py-6 sm:px-6">
      <article className="rg-doc-surface mx-auto max-w-6xl bg-white shadow-xl rounded-sm border border-slate-200 overflow-hidden">
        <header className="border-b border-slate-200 px-5 py-4 sm:px-8 bg-gradient-to-r from-slate-50 to-white">
          <p className="rg-doc-eyebrow text-[11px] font-bold tracking-wide uppercase">
            Reg Guard · IC Diligence Bundle
          </p>
          <h1 className="rg-doc-title text-xl sm:text-2xl font-black mt-1 leading-tight">
            {title}
          </h1>
          <p className="rg-doc-muted text-xs mt-1">
            {isCover
              ? 'Cover summary — open Fees / Punch / Evidence tabs for the full schedules.'
              : 'Finished workbook preview — planning aid, not a sealed bid or AHJ filing.'}
          </p>
        </header>
        {sheets.length > 1 ? (
          <div className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-slate-50 px-3 py-2">
            {sheets.map((s, i) => (
              <button
                key={s.name}
                type="button"
                onClick={() => onSelect(i)}
                className={`rg-sheet-tab shrink-0 px-3 py-1.5 rounded-md text-xs font-semibold min-h-[36px] ${
                  i === active ? 'rg-sheet-tab-active' : ''
                }`}
              >
                {s.name}
              </button>
            ))}
          </div>
        ) : null}
        {intro.length > 0 ? (
          <div className="px-5 py-3 border-b border-slate-100 bg-slate-50 space-y-1">
            {intro.map((line, i) => (
              <p key={`intro-${i}`} className="rg-doc-muted text-xs sm:text-sm leading-relaxed">
                {line}
              </p>
            ))}
          </div>
        ) : null}
        <div className="overflow-auto max-h-[75vh]">
          <table className="w-full text-left text-xs sm:text-sm border-collapse">
            <thead className="sticky top-0 z-10 bg-slate-800">
              <tr>
                {headers.map((cell, i) => (
                  <th
                    key={`h-${i}`}
                    className="rg-sheet-th px-3 py-2.5 font-bold whitespace-nowrap border-r border-slate-700 last:border-r-0"
                  >
                    {cell || `Col ${i + 1}`}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.length === 0 ? (
                <tr>
                  <td
                    className="rg-sheet-td px-3 py-4"
                    colSpan={Math.max(headers.length, 1)}
                  >
                    No data rows on this sheet.
                  </td>
                </tr>
              ) : (
                body.map((row, ri) => (
                  <tr key={`r-${ri}`} className={ri % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                    {headers.map((_, ci) => {
                      const val = row[ci] ?? '';
                      const isUrl = /^https?:\/\//i.test(val);
                      return (
                        <td
                          key={`c-${ri}-${ci}`}
                          className="rg-sheet-td px-3 py-2 align-top border-b border-slate-100 max-w-[320px] break-words"
                        >
                          {isUrl ? (
                            <a href={val} target="_blank" rel="noopener noreferrer">
                              {val.length > 64 ? `${val.slice(0, 62)}…` : val}
                            </a>
                          ) : (
                            val
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <footer className="rg-doc-muted px-5 py-3 border-t border-slate-200 text-[11px] bg-slate-50">
          {body.length} data row{body.length === 1 ? '' : 's'}
          {sheets.length > 1 ? ` · sheet “${sheet.name}”` : ''}
          {!isCover && sheets.some((s) => s.isCover)
            ? ' · Cover tab has stamp / contingency summary'
            : ''}
        </footer>
      </article>
    </div>
  );
}

export function DocxPreview({ blobUrl, filename }: { blobUrl: string; filename: string }) {
  const [html, setHtml] = useState<string | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    let cancelled = false;
    setHtml(null);
    setErr('');
    void (async () => {
      try {
        const res = await fetch(blobUrl);
        const buf = await res.arrayBuffer();
        const result = await mammoth.convertToHtml({ arrayBuffer: buf });
        if (!cancelled) setHtml(result.value || '<p>(Empty document)</p>');
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Could not preview DOCX');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [blobUrl]);

  if (err) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-amber-200 text-sm">{err}</div>
    );
  }
  if (html == null) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-gray-400 text-sm">
        Loading counsel document…
      </div>
    );
  }

  return (
    <div className="min-h-full bg-[#e8edf5] px-3 py-6 sm:px-6 overflow-auto">
      <article className="rg-doc-surface mx-auto max-w-3xl bg-white shadow-xl rounded-sm border border-slate-200 px-6 py-8 sm:px-10 sm:py-10">
        <p className="rg-doc-eyebrow text-[11px] font-bold tracking-wide uppercase mb-2">
          Reg Guard · Counsel DOCX Preview
        </p>
        <h1 className="rg-doc-title text-xl sm:text-2xl font-black mb-6 leading-tight">
          {humanTitle(filename)}
        </h1>
        <div
          className="rg-docx-preview text-[15px] leading-relaxed
            [&_h1]:text-2xl [&_h1]:font-black [&_h1]:mt-6 [&_h1]:mb-3
            [&_h2]:text-xl [&_h2]:font-bold [&_h2]:mt-5 [&_h2]:mb-2
            [&_h3]:text-lg [&_h3]:font-bold [&_h3]:mt-4 [&_h3]:mb-2
            [&_p]:mb-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5
            [&_table]:w-full [&_table]:border-collapse [&_td]:border [&_td]:border-slate-200 [&_td]:px-2 [&_td]:py-1
            [&_th]:border [&_th]:border-slate-300 [&_th]:bg-slate-100 [&_th]:px-2 [&_th]:py-1 [&_th]:text-left"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </article>
    </div>
  );
}

export function SheetPreviewPanel({
  blobUrl,
  filename,
}: {
  blobUrl: string;
  filename: string;
}) {
  const [sheets, setSheets] = useState<SheetPreview[] | null>(null);
  const [active, setActive] = useState(0);
  const [err, setErr] = useState('');

  useEffect(() => {
    let cancelled = false;
    setSheets(null);
    setActive(0);
    setErr('');
    void (async () => {
      try {
        const res = await fetch(blobUrl);
        const buf = await res.arrayBuffer();
        const lower = (filename || '').toLowerCase();
        let wb: XLSX.WorkBook;
        if (lower.endsWith('.csv')) {
          // Strip BOM; SheetJS handles CRLF
          let text = new TextDecoder('utf-8').decode(buf);
          if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
          wb = XLSX.read(text, { type: 'string', FS: ',', raw: false });
          if (wb.SheetNames.length === 1) {
            wb.SheetNames[0] = humanTitle(filename) || 'Schedule';
          }
        } else {
          wb = XLSX.read(buf, { type: 'array', cellDates: true });
        }
        const parsed = workbookToSheets(wb);
        if (!cancelled) {
          setSheets(parsed);
          setActive(defaultActiveIndex(parsed));
        }
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Could not preview spreadsheet');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [blobUrl, filename]);

  if (err) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-amber-200 text-sm">{err}</div>
    );
  }
  if (!sheets) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-gray-400 text-sm">
        Loading workbook…
      </div>
    );
  }

  return (
    <SheetDocument
      title={humanTitle(filename)}
      sheets={sheets}
      active={active}
      onSelect={setActive}
    />
  );
}
