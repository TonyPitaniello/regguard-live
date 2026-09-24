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
  rows: string[][];
};

function workbookToSheets(wb: XLSX.WorkBook): SheetPreview[] {
  return wb.SheetNames.map((name) => {
    const sheet = wb.Sheets[name];
    const rows = XLSX.utils.sheet_to_json<string[]>(sheet, {
      header: 1,
      defval: '',
      raw: false,
    }) as string[][];
    return {
      name,
      rows: rows.map((r) => (Array.isArray(r) ? r.map((c) => String(c ?? '')) : [])),
    };
  }).filter((s) => s.rows.some((r) => r.some((c) => String(c).trim())));
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
  const header = sheet.rows[0] || [];
  const body = sheet.rows.slice(1);

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
            Finished workbook preview — planning aid, not a sealed bid or AHJ filing.
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
        <div className="overflow-auto max-h-[75vh]">
          <table className="w-full text-left text-xs sm:text-sm border-collapse">
            <thead className="sticky top-0 z-10 bg-slate-800">
              <tr>
                {header.map((cell, i) => (
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
              {body.map((row, ri) => (
                <tr
                  key={`r-${ri}`}
                  className={ri % 2 === 0 ? 'bg-white' : 'bg-slate-50'}
                >
                  {header.map((_, ci) => (
                    <td
                      key={`c-${ri}-${ci}`}
                      className="rg-sheet-td px-3 py-2 align-top border-b border-slate-100 max-w-[280px] break-words"
                    >
                      {row[ci] ?? ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <footer className="rg-doc-muted px-5 py-3 border-t border-slate-200 text-[11px] bg-slate-50">
          {body.length} data row{body.length === 1 ? '' : 's'}
          {sheets.length > 1 ? ` · sheet “${sheet.name}”` : ''}
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
          const text = new TextDecoder('utf-8').decode(buf);
          wb = XLSX.read(text, { type: 'string', FS: ',' });
          if (wb.SheetNames.length === 1) {
            wb.SheetNames[0] = humanTitle(filename) || 'Schedule';
          }
        } else {
          wb = XLSX.read(buf, { type: 'array' });
        }
        const parsed = workbookToSheets(wb);
        if (!cancelled) setSheets(parsed);
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
