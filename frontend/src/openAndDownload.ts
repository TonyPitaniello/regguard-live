/**
 * Open a file in the in-app viewer and download it.
 * Used by sample CTAs and Results / Orders artifact downloads.
 */

import {
  getStashedFile,
  isPreviewableMime,
  markStashedDownloaded,
  stashFileBlob,
} from './fileViewStore';
import { appNavigate } from './navigationBridge';

function triggerBrowserDownload(blobUrl: string, filename: string): void {
  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/** Download + navigate to in-app viewer for a Blob already in hand. */
export async function openAndDownloadBlob(blob: Blob, filename: string): Promise<string> {
  if (!blob || blob.size < 40) {
    throw new Error('File was empty — try again.');
  }
  const id = stashFileBlob(blob, filename);
  const file = getStashedFile(id);
  if (!file) throw new Error('Could not prepare file viewer.');

  triggerBrowserDownload(file.blobUrl, file.filename);
  markStashedDownloaded(id);

  appNavigate(`/view-file?id=${encodeURIComponent(id)}`);
  return id;
}

/** Fetch a same-origin or absolute URL, then open + download. */
export async function openAndDownloadUrl(url: string, filename?: string): Promise<string> {
  const res = await fetch(url, { credentials: 'omit' });
  if (!res.ok) {
    throw new Error(`Download failed (${res.status})`);
  }
  const blob = await res.blob();
  const name =
    filename ||
    url.split('/').pop()?.split('?')[0] ||
    (isPreviewableMime(blob.type, '') ? 'RegGuard_document.pdf' : 'RegGuard_file');
  return openAndDownloadBlob(blob, name);
}

/** Re-download from an already-stashed viewer file. */
export function redownloadStashed(id: string): void {
  const file = getStashedFile(id);
  if (!file) return;
  triggerBrowserDownload(file.blobUrl, file.filename);
  markStashedDownloaded(id);
}
