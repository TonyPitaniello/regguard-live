/**
 * In-memory stash for files opened in the in-app viewer.
 * Survives client-side React Router navigations (same document).
 */

export type StashedFile = {
  id: string;
  blobUrl: string;
  filename: string;
  mime: string;
  size: number;
  downloaded: boolean;
};

const stash = new Map<string, StashedFile>();

export function stashFileBlob(blob: Blob, filename: string): string {
  const id =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `f-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  const blobUrl = URL.createObjectURL(blob);
  stash.set(id, {
    id,
    blobUrl,
    filename: filename || 'RegGuard_file',
    mime: blob.type || guessMime(filename),
    size: blob.size,
    downloaded: false,
  });
  return id;
}

export function getStashedFile(id: string): StashedFile | null {
  return stash.get(id) || null;
}

export function markStashedDownloaded(id: string): void {
  const f = stash.get(id);
  if (f) f.downloaded = true;
}

export function releaseStashedFile(id: string): void {
  const f = stash.get(id);
  if (!f) return;
  try {
    URL.revokeObjectURL(f.blobUrl);
  } catch {
    /* ignore */
  }
  stash.delete(id);
}

function guessMime(filename: string): string {
  const n = filename.toLowerCase();
  if (n.endsWith('.pdf')) return 'application/pdf';
  if (n.endsWith('.zip')) return 'application/zip';
  if (n.endsWith('.docx'))
    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  if (n.endsWith('.xlsx'))
    return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
  if (n.endsWith('.csv')) return 'text/csv';
  return 'application/octet-stream';
}

export function isPreviewableMime(mime: string, filename: string): boolean {
  const m = (mime || '').toLowerCase();
  const n = (filename || '').toLowerCase();
  return m.includes('pdf') || n.endsWith('.pdf');
}
