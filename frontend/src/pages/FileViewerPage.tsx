/**
 * In-app file viewer — scrollable PDF / text preview + download + forward.
 * ZIP packages unpack to member tabs (PDFs first).
 */

import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Download, Eye, FileArchive, FileText, Share2 } from 'lucide-react';
import {
  getStashedFile,
  releaseStashedFile,
  setActiveMember,
  type StashedFile,
} from '../fileViewStore';
import {
  downloadActiveMember,
  forwardStashed,
  redownloadStashed,
} from '../openAndDownload';

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileViewerPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const id = (params.get('id') || '').trim();
  const [file, setFile] = useState<StashedFile | null>(null);
  const [missing, setMissing] = useState(false);
  const [textBody, setTextBody] = useState<string | null>(null);
  const [forwardNote, setForwardNote] = useState('');

  useEffect(() => {
    if (!id) {
      setMissing(true);
      return;
    }
    const stashed = getStashedFile(id);
    if (!stashed) {
      setMissing(true);
      return;
    }
    setFile({ ...stashed });
    setMissing(false);
  }, [id]);

  useEffect(() => {
    if (!file || file.previewKind !== 'text') {
      setTextBody(null);
      return;
    }
    let cancelled = false;
    void fetch(file.blobUrl)
      .then((r) => r.text())
      .then((t) => {
        if (!cancelled) setTextBody(t);
      })
      .catch(() => {
        if (!cancelled) setTextBody('(Could not load text preview.)');
      });
    return () => {
      cancelled = true;
    };
  }, [file?.blobUrl, file?.previewKind]);

  const onBack = () => {
    if (id) releaseStashedFile(id);
    if (window.history.length > 1) navigate(-1);
    else navigate('/');
  };

  const selectMember = (name: string) => {
    if (!id) return;
    const next = setActiveMember(id, name);
    if (next) setFile({ ...next });
  };

  const onForward = async () => {
    if (!id) return;
    setForwardNote('');
    const result = await forwardStashed(id);
    if (result === 'shared') setForwardNote('Shared');
    else if (result === 'copied') setForwardNote('Forward text copied');
    else setForwardNote('Share unavailable — use Download');
    window.setTimeout(() => setForwardNote(''), 2500);
  };

  if (missing || !file) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-900 to-[#0a1429] text-white flex flex-col items-center justify-center px-4">
        <p className="text-lg font-bold mb-2">File session expired</p>
        <p className="text-gray-300 text-sm mb-6 text-center max-w-md">
          Open the file again from the sample list or your results — the viewer needs a fresh file
          from this browser session.
        </p>
        <Link
          to="/"
          className="px-5 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-bold min-h-[44px]"
        >
          Back to home
        </Link>
      </div>
    );
  }

  const packageLabel = file.packageFilename || file.filename;
  const hasPackage = Boolean(file.packageBlobUrl && file.packageFilename);
  const members = file.members || [];

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-900/95 backdrop-blur px-3 py-3 sm:px-4 flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2 justify-between">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-2 text-emerald-300 hover:text-white font-semibold min-h-[44px]"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <div className="min-w-0 flex-1 text-center sm:text-left px-1">
            <p className="font-bold text-sm sm:text-base truncate">{file.filename}</p>
            <p className="text-xs text-gray-400 truncate">
              {hasPackage ? `Inside ${packageLabel} · ` : ''}
              Viewing in Reg Guard · {formatBytes(file.size)}
              {file.downloaded ? ' · Also saved to Downloads' : ''}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 w-full max-w-lg mx-auto sm:max-w-none sm:mx-0 sm:flex sm:flex-wrap sm:justify-end">
          <button
            type="button"
            onClick={() => downloadActiveMember(id)}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg border border-emerald-400/50 bg-[#0f1d38] hover:bg-emerald-500/20 text-emerald-200 font-bold text-xs sm:text-sm min-h-[44px]"
            title="Download this page"
          >
            <Eye className="w-4 h-4 shrink-0" />
            <span className="truncate">This file</span>
          </button>
          <button
            type="button"
            onClick={() => redownloadStashed(id)}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 font-bold text-xs sm:text-sm min-h-[44px]"
            title={`Download ${packageLabel}`}
          >
            <Download className="w-4 h-4 shrink-0" />
            <span className="truncate">{hasPackage ? 'Save ZIP' : 'Save'}</span>
          </button>
          <button
            type="button"
            onClick={() => void onForward()}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg border border-white/20 bg-white/5 hover:bg-white/10 font-bold text-xs sm:text-sm min-h-[44px]"
            title="Forward / share"
          >
            <Share2 className="w-4 h-4 shrink-0" />
            <span className="truncate">Forward</span>
          </button>
        </div>
        {forwardNote ? (
          <p className="text-center text-xs text-emerald-300 font-semibold">{forwardNote}</p>
        ) : null}
      </header>

      {members.length > 1 ? (
        <div className="border-b border-white/10 bg-slate-900/80 px-3 py-2 overflow-x-auto">
          <div className="flex gap-2 min-w-min">
            {members.map((m) => {
              const active = m.name === file.activeMember || m.name === file.filename;
              return (
                <button
                  key={m.name}
                  type="button"
                  onClick={() => selectMember(m.name)}
                  className={`shrink-0 px-3 py-2 rounded-lg text-xs font-semibold min-h-[40px] border transition ${
                    active
                      ? 'border-emerald-400 bg-emerald-500/20 text-white'
                      : 'border-white/10 bg-white/5 text-gray-300 hover:border-emerald-400/40'
                  }`}
                >
                  {m.previewKind === 'pdf' ? 'PDF · ' : m.previewKind === 'text' ? '' : ''}
                  {m.name.length > 36 ? `${m.name.slice(0, 34)}…` : m.name}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <main className="flex-1 flex flex-col min-h-0">
        {file.previewKind === 'pdf' ? (
          <iframe
            title={file.filename}
            src={file.blobUrl}
            className="flex-1 w-full min-h-[70vh] bg-white border-0"
          />
        ) : file.previewKind === 'text' ? (
          <pre className="flex-1 overflow-auto p-4 sm:p-6 text-sm text-emerald-50/95 bg-[#0a1429] whitespace-pre-wrap break-words font-mono leading-relaxed">
            {textBody ?? 'Loading…'}
          </pre>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-16 text-center">
            {packageLabel.toLowerCase().endsWith('.zip') || file.mime.includes('zip') ? (
              <FileArchive className="w-14 h-14 text-emerald-300 mb-4" />
            ) : (
              <FileText className="w-14 h-14 text-emerald-300 mb-4" />
            )}
            <h1 className="text-2xl font-black mb-2">Open on your device</h1>
            <p className="text-gray-300 max-w-md mb-6 leading-relaxed">
              This file type ({file.filename.split('.').pop()?.toUpperCase() || 'binary'}) needs an
              office app. Save it, then open in Word / Excel / Finder. Prefer PDF members above when
              listed.
            </p>
            <button
              type="button"
              onClick={() => downloadActiveMember(id)}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-bold min-h-[48px]"
            >
              <Download className="w-5 h-5" />
              Download {file.filename}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
