/**
 * Open a file in the in-app viewer and/or force a disk download.
 * ZIPs unpack so PDFs / text scroll in-app; Save still gets the original package.
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

function goToViewer(id: string, opts?: NavOpts): void {
  const to = `/view-file?id=${encodeURIComponent(id)}`;
  if (opts?.navigate) opts.navigate(to);
  else appNavigate(to);
}

/** Open in-app /view-file only (no disk download). Unpacks ZIP → scrollable PDF/text. */
export async function viewInAppBlob(
  blob: Blob,
  filename: string,
  opts?: NavOpts
): Promise<string> {
  if (!blob || blob.size < 40) throw new Error('File was empty — try again.');
  const id = await stashFileBlob(blob, filename);
  goToViewer(id, opts);
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
 * Open viewer (scrollable) + download original package to disk.
 * Used by Results / Orders / PDF export.
 */
export async function openAndDownloadBlob(
  blob: Blob,
  filename: string,
  opts?: NavOpts
): Promise<string> {
  if (!blob || blob.size < 40) {
    throw new Error('File was empty — try again.');
  }
  const id = await stashFileBlob(blob, filename);
  const file = getStashedFile(id);
  if (!file) throw new Error('Could not prepare file viewer.');

  goToViewer(id, opts);

  // Always save the original package (ZIP or PDF), not just the previewed member
  window.setTimeout(() => {
    const packageUrl = file.packageBlobUrl || file.blobUrl;
    const packageName = file.packageFilename || file.filename;
    void fetch(packageUrl)
      .then((r) => r.blob())
      .then((b) => {
        triggerBrowserDownload(b, packageName);
        markStashedDownloaded(id);
      })
      .catch(() => {
        triggerBrowserDownload(blob, filename);
        markStashedDownloaded(id);
      });
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

/** Re-download package (or current file) from an already-stashed viewer session. */
export function redownloadStashed(id: string): void {
  const file = getStashedFile(id);
  if (!file) return;
  const url = file.packageBlobUrl || file.blobUrl;
  const name = file.packageFilename || file.filename;
  void fetch(url)
    .then((r) => r.blob())
    .then((b) => {
      triggerBrowserDownload(b, name);
      markStashedDownloaded(id);
    })
    .catch(() => {
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
}

/** Download only the currently previewed member. */
export function downloadActiveMember(id: string): void {
  const file = getStashedFile(id);
  if (!file) return;
  void fetch(file.blobUrl)
    .then((r) => r.blob())
    .then((b) => {
      triggerBrowserDownload(b, file.filename);
    })
    .catch(() => undefined);
}

/** Native share / copy forward text for the stashed package. */
export async function forwardStashed(id: string): Promise<'shared' | 'copied' | 'failed'> {
  const file = getStashedFile(id);
  if (!file) return 'failed';
  const name = file.packageFilename || file.filename;
  const url = file.packageBlobUrl || file.blobUrl;
  try {
    const blob = await (await fetch(url)).blob();
    const shareFile = new File([blob], name, {
      type: blob.type || 'application/octet-stream',
    });
    if (typeof navigator !== 'undefined' && navigator.share) {
      const canFiles =
        !navigator.canShare || navigator.canShare({ files: [shareFile] });
      if (canFiles) {
        await navigator.share({
          files: [shareFile],
          title: 'Reg Guard',
          text: `Reg Guard — Citeable Bid Risk Receipt — before you bid.\n${name}`,
        });
        return 'shared';
      }
      await navigator.share({
        title: 'Reg Guard',
        text: `Reg Guard — Citeable Bid Risk Receipt — before you bid.\n${name}`,
      });
      return 'shared';
    }
  } catch (e) {
    // User cancel vs hard fail
    if (e instanceof Error && /AbortError|canceled|cancelled/i.test(e.message)) {
      return 'failed';
    }
  }
  try {
    const text = `Reg Guard — Citeable Bid Risk Receipt — before you bid.\n${name}\nOpen in Reg Guard to download.\nPlanning aid only — confirm with AHJ before bid.`;
    await navigator.clipboard.writeText(text);
    return 'copied';
  } catch {
    return 'failed';
  }
}
