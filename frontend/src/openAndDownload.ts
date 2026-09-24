/**
 * Open a file in the in-app viewer and/or force a disk download.
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

async function fetchBlob(url: string): Promise<Blob> {
  const res = await fetch(url, { credentials: 'omit' });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  return res.blob();
}

function resolveFilename(url: string, filename: string | undefined, blob: Blob): string {
  return (
    filename ||
    url.split('/').pop()?.split('?')[0] ||
    (isPreviewableMime(blob.type, '') ? 'RegGuard_document.pdf' : 'RegGuard_file')
  );
}

/** Open in-app /view-file only (no disk download). */
export async function viewInAppBlob(
  blob: Blob,
  filename: string,
  opts?: NavOpts
): Promise<string> {
  if (!blob || blob.size < 40) throw new Error('File was empty — try again.');
  const id = stashFileBlob(blob, filename);
  const to = `/view-file?id=${encodeURIComponent(id)}`;
  if (opts?.navigate) opts.navigate(to);
  else appNavigate(to);
  return id;
}

/** Download to disk only (no navigation). */
export async function downloadOnlyBlob(blob: Blob, filename: string): Promise<void> {
  if (!blob || blob.size < 40) throw new Error('File was empty — try again.');
  triggerBrowserDownload(blob, filename);
}

/** Fetch URL → open in-app viewer only. */
export async function viewInAppUrl(
  url: string,
  filename?: string,
  opts?: NavOpts
): Promise<string> {
  const blob = await fetchBlob(url);
  return viewInAppBlob(blob, resolveFilename(url, filename, blob), opts);
}

/** Fetch URL → disk download only. */
export async function downloadOnlyUrl(url: string, filename?: string): Promise<void> {
  const blob = await fetchBlob(url);
  await downloadOnlyBlob(blob, resolveFilename(url, filename, blob));
}

/**
 * Legacy combined path (Results/Orders artifacts): open viewer + download.
 * Prefer viewInApp* / downloadOnly* for sample CTAs.
 */
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
  if (opts?.navigate) opts.navigate(to);
  else appNavigate(to);

  window.setTimeout(() => {
    triggerBrowserDownload(blob, file.filename);
    markStashedDownloaded(id);
  }, 50);

  return id;
}

export async function openAndDownloadUrl(
  url: string,
  filename?: string,
  opts?: NavOpts
): Promise<string> {
  const blob = await fetchBlob(url);
  return openAndDownloadBlob(blob, resolveFilename(url, filename, blob), opts);
}

/** Re-download from an already-stashed viewer file. */
export function redownloadStashed(id: string): void {
  const file = getStashedFile(id);
  if (!file) return;
  void fetch(file.blobUrl)
    .then((r) => r.blob())
    .then((b) => {
      triggerBrowserDownload(b, file.filename);
      markStashedDownloaded(id);
    })
    .catch(() => {
      const a = document.createElement('a');
      a.href = file.blobUrl;
      a.download = file.filename;
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
}
