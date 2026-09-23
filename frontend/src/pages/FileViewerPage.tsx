/**
 * In-app file viewer — PDF preview + download again.
 * ZIP / DOCX / CSV show a ready card (browser cannot inline-preview).
 */

import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Download, FileArchive, FileText } from 'lucide-react';
import {
  getStashedFile,
  isPreviewableMime,
  releaseStashedFile,
  type StashedFile,
} from '../fileViewStore';
import { redownloadStashed } from '../openAndDownload';

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
    setFile(stashed);
    setMissing(false);
  }, [id]);

  useEffect(() => {
    return () => {
      // Keep blob alive while viewing; revoke only on explicit leave via Back
    };
  }, []);

  const previewable = useMemo(
    () => (file ? isPreviewableMime(file.mime, file.filename) : false),
    [file]
  );

  const onBack = () => {
    if (id) releaseStashedFile(id);
    if (window.history.length > 1) navigate(-1);
    else navigate('/');
  };

  if (missing || !file) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white flex flex-col items-center justify-center px-4">
        <p className="text-lg font-bold mb-2">File session expired</p>
        <p className="text-gray-300 text-sm mb-6 text-center max-w-md">
          Open the download again from the sample list or your results — the viewer needs a fresh
          file from this browser session.
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

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-900/95 backdrop-blur px-4 py-3 flex flex-wrap items-center gap-3 justify-between">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 text-emerald-300 hover:text-white font-semibold min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <div className="min-w-0 flex-1 text-center sm:text-left">
          <p className="font-bold text-sm sm:text-base truncate">{file.filename}</p>
          <p className="text-xs text-gray-400">
            {formatBytes(file.size)}
            {file.downloaded ? ' · Downloaded to your device' : ''}
          </p>
        </div>
        <button
          type="button"
          onClick={() => redownloadStashed(file.id)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-bold text-sm min-h-[44px]"
        >
          <Download className="w-4 h-4" />
          Download again
        </button>
      </header>

      <main className="flex-1 flex flex-col min-h-0">
        {previewable ? (
          <iframe
            title={file.filename}
            src={file.blobUrl}
            className="flex-1 w-full min-h-[70vh] bg-white border-0"
          />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-16 text-center">
            {file.filename.toLowerCase().endsWith('.zip') ? (
              <FileArchive className="w-14 h-14 text-emerald-300 mb-4" />
            ) : (
              <FileText className="w-14 h-14 text-emerald-300 mb-4" />
            )}
            <h1 className="text-2xl font-black mb-2">File ready</h1>
            <p className="text-gray-300 max-w-md mb-6 leading-relaxed">
              {file.filename.toLowerCase().endsWith('.zip')
                ? 'ZIP packages download to your device — open the archive in Finder or Explorer to see every file inside.'
                : 'This file type opens best after download. Use Download again if you need another copy.'}
            </p>
            <button
              type="button"
              onClick={() => redownloadStashed(file.id)}
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
