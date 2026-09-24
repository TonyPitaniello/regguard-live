/**
 * Open a file in the in-app viewer and force a disk download.
 * Browsers often inline application/pdf — we download via octet-stream instead.
 */

import {
  getStashedFile,
  isPreviewableMime,
  markStashedDownloaded,
  stashFileBlob,
} from './fileViewStore';
import { appNavigate } from './navigationBridge';

/** Force a Save As / Downloads hit (never navigate the tab to the PDF). */
export function triggerBrowserDownload(blob: Blob, filename: string): void {
  // octet-stream + download attr prevents Chrome/Safari from opening a PDF tab
  const forceBlob = new Blob([blob], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(forceBlob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || 'RegGuard_file';
  a.rel = 'noopener';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => {
    try {
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  }, 60_000);
}

type NavOpts = {
  /** Prefer React Router navigate when caller has it */
  navigate?: (to: string) => void;
};

/** Download + open in-app /view-file for a Blob already in hand. */
export async function openAndDownloadBlob(
  blob: Blob,
  filename: string,
  opts?: NavOpts
): Promise<string> {
  if (!blob || blob.size < 40) {
    throw new Error('File was empty — try again.');
  }
  const id = stashFileBlob(blob, filename);
  const file = getStashedFile(id);
  if (!file) throw new Error('Could not prepare file viewer.');

  const to = `/view-file?id=${encodeURIComponent(id)}`;
  // Navigate first so the app viewer mounts; then force disk download
  if (opts?.navigate) opts.navigate(to);
  else appNavigate(to);

  window.setTimeout(() => {
    triggerBrowserDownload(blob, file.filename);
    markStashedDownloaded(id);
  }, 50);

  return id;
}

/** Fetch a same-origin or absolute URL, then open + download. */
export async function openAndDownloadUrl(
  url: string,
  filename?: string,
  opts?: NavOpts
): Promise<string> {
  const res = await fetch(url, { credentials: 'omit' });
  if (!res.ok) {
    throw new Error(`Download failed (${res.status})`);
  }
  const blob = await res.blob();
  const name =
    filename ||
    url.split('/').pop()?.split('?')[0] ||
    (isPreviewableMime(blob.type, '') ? 'RegGuard_document.pdf' : 'RegGuard_file');
  return openAndDownloadBlob(blob, name, opts);
}

/** Re-download from an already-stashed viewer file. */
export function redownloadStashed(id: string): void {
  const file = getStashedFile(id);
  if (!file) return;
  // Fetch bytes back from the preview URL so we can re-wrap as octet-stream
  void fetch(file.blobUrl)
    .then((r) => r.blob())
    .then((b) => {
      triggerBrowserDownload(b, file.filename);
      markStashedDownloaded(id);
    })
    .catch(() => {
      // Fallback: try download attr on preview URL (may inline PDF on some browsers)
      const a = document.createElement('a');
      a.href = file.blobUrl;
      a.download = file.filename;
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
}
