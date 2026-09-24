/**
 * In-memory stash for files opened in the in-app viewer.
 * Survives client-side React Router navigations (same document).
 * ZIP packages are unpacked so PDFs / DOCX / sheets can scroll in-app.
 */

import { unzipSync } from 'fflate';

export type PreviewKind = 'pdf' | 'text' | 'docx' | 'sheet' | 'none';

export type StashedMember = {
  name: string;
  blobUrl: string;
  mime: string;
  size: number;
  previewKind: PreviewKind;
};

export type StashedFile = {
  id: string;
  /** Active member blob URL (or sole file) */
  blobUrl: string;
  filename: string;
  mime: string;
  size: number;
  downloaded: boolean;
  previewKind: PreviewKind;
  /** Original package (ZIP) for Save / Forward when viewing an extracted member */
  packageFilename?: string;
  packageBlobUrl?: string;
  members?: StashedMember[];
  activeMember?: string;
};

const stash = new Map<string, StashedFile>();

export function guessMime(filename: string): string {
  const n = filename.toLowerCase();
  if (n.endsWith('.pdf')) return 'application/pdf';
  if (n.endsWith('.zip')) return 'application/zip';
  if (n.endsWith('.docx'))
    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  if (n.endsWith('.xlsx') || n.endsWith('.xls'))
    return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
  if (n.endsWith('.csv')) return 'text/csv';
  if (n.endsWith('.json')) return 'application/json';
  if (n.endsWith('.txt') || n.endsWith('.md')) return 'text/plain';
  if (n.endsWith('.html') || n.endsWith('.htm')) return 'text/html';
  return 'application/octet-stream';
}

export function previewKindFor(mime: string, filename: string): PreviewKind {
  const m = (mime || '').toLowerCase();
  const n = (filename || '').toLowerCase();
  if (m.includes('pdf') || n.endsWith('.pdf')) return 'pdf';
  if (
    m.includes('wordprocessingml') ||
    m.includes('msword') ||
    n.endsWith('.docx') ||
    n.endsWith('.doc')
  ) {
    return 'docx';
  }
  if (
    m.includes('spreadsheetml') ||
    m.includes('excel') ||
    m.includes('csv') ||
    n.endsWith('.xlsx') ||
    n.endsWith('.xls') ||
    n.endsWith('.csv')
  ) {
    return 'sheet';
  }
  if (
    m.startsWith('text/') ||
    m.includes('json') ||
    n.endsWith('.txt') ||
    n.endsWith('.md') ||
    n.endsWith('.json') ||
    n.endsWith('.html') ||
    n.endsWith('.htm')
  ) {
    return 'text';
  }
  return 'none';
}

/** @deprecated use previewKindFor */
export function isPreviewableMime(mime: string, filename: string): boolean {
  return previewKindFor(mime, filename) !== 'none';
}

function scoreMemberName(name: string): number {
  const n = name.toLowerCase();
  let score = 0;
  if (n.endsWith('.pdf')) score += 100;
  if (n.includes('boardroom') || n.includes('ic_diligence') || n.includes('ic-project')) score += 40;
  if (n.includes('receipt') || n.includes('bid_risk') || n.includes('memo')) score += 30;
  if (n.includes('city_pack') || n.includes('city-pack')) score += 20;
  if (n.includes('readme')) score -= 50;
  if (n.endsWith('.docx')) score += 25;
  if (n.endsWith('.xlsx') || n.endsWith('.xls')) score += 20;
  if (n.endsWith('.csv')) score += 10;
  // Prefer shorter paths / numbered primary docs
  if (/^\d{2}_/.test(name.split('/').pop() || '')) score += 10;
  return score;
}

function typedBlob(raw: Blob | Uint8Array, filename: string, mimeHint?: string): Blob {
  const mime = mimeHint || guessMime(filename);
  if (raw instanceof Blob) {
    if (raw.type && raw.type !== 'application/octet-stream') return raw;
    return new Blob([raw], { type: mime });
  }
  return new Blob([raw], { type: mime });
}

function makeMember(name: string, data: Uint8Array): StashedMember {
  const base = name.split('/').pop() || name;
  const mime = guessMime(base);
  const blob = typedBlob(data, base, mime);
  return {
    name: base,
    blobUrl: URL.createObjectURL(blob),
    mime,
    size: blob.size,
    previewKind: previewKindFor(mime, base),
  };
}

/** Prefer the best scrollable member from a ZIP; keep package for Save. */
export async function expandBlobForViewer(
  blob: Blob,
  filename: string
): Promise<{
  displayBlob: Blob;
  displayName: string;
  mime: string;
  previewKind: PreviewKind;
  members?: StashedMember[];
  packageBlob?: Blob;
  packageFilename?: string;
}> {
  const lower = (filename || '').toLowerCase();
  const mime0 = blob.type || guessMime(filename);
  const isZip =
    lower.endsWith('.zip') ||
    mime0.includes('zip') ||
    (mime0.includes('octet-stream') && lower.endsWith('.zip'));

  if (!isZip && !lower.endsWith('.zip')) {
    const typed = typedBlob(blob, filename, mime0);
    return {
      displayBlob: typed,
      displayName: filename || 'RegGuard_file',
      mime: typed.type,
      previewKind: previewKindFor(typed.type, filename),
    };
  }

  try {
    const buf = new Uint8Array(await blob.arrayBuffer());
    // ZIP local header magic
    if (buf.length < 4 || buf[0] !== 0x50 || buf[1] !== 0x4b) {
      const typed = typedBlob(blob, filename, mime0);
      return {
        displayBlob: typed,
        displayName: filename,
        mime: typed.type,
        previewKind: previewKindFor(typed.type, filename),
      };
    }
    const files = unzipSync(buf);
    const members: StashedMember[] = [];
    for (const [path, data] of Object.entries(files)) {
      if (!data || !data.length) continue;
      const base = path.split('/').pop() || path;
      if (!base || base.startsWith('.')) continue;
      members.push(makeMember(path, data));
    }
    members.sort((a, b) => scoreMemberName(b.name) - scoreMemberName(a.name));
    if (!members.length) {
      const typed = typedBlob(blob, filename, 'application/zip');
      return {
        displayBlob: typed,
        displayName: filename,
        mime: 'application/zip',
        previewKind: 'none',
        packageBlob: typed,
        packageFilename: filename,
      };
    }

    const best =
      members.find((m) => m.previewKind === 'pdf') ||
      members.find((m) => m.previewKind === 'docx') ||
      members.find((m) => m.previewKind === 'sheet') ||
      members.find((m) => m.previewKind === 'text') ||
      members[0];

    const packageBlob = typedBlob(blob, filename, 'application/zip');
    // Rebuild display blob from best member URL's underlying data via fetch
    const bestRes = await fetch(best.blobUrl);
    const displayBlob = await bestRes.blob();

    return {
      displayBlob: typedBlob(displayBlob, best.name, best.mime),
      displayName: best.name,
      mime: best.mime,
      previewKind: best.previewKind,
      members,
      packageBlob,
      packageFilename: filename,
    };
  } catch {
    const typed = typedBlob(blob, filename, mime0);
    return {
      displayBlob: typed,
      displayName: filename,
      mime: typed.type,
      previewKind: previewKindFor(typed.type, filename),
    };
  }
}

export async function stashFileBlob(blob: Blob, filename: string): Promise<string> {
  const id =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `f-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

  const expanded = await expandBlobForViewer(blob, filename || 'RegGuard_file');
  const displayUrl = URL.createObjectURL(expanded.displayBlob);
  let packageBlobUrl: string | undefined;
  if (expanded.packageBlob) {
    packageBlobUrl = URL.createObjectURL(expanded.packageBlob);
  }

  stash.set(id, {
    id,
    blobUrl: displayUrl,
    filename: expanded.displayName,
    mime: expanded.mime,
    size: expanded.displayBlob.size,
    downloaded: false,
    previewKind: expanded.previewKind,
    packageFilename: expanded.packageFilename,
    packageBlobUrl,
    members: expanded.members,
    activeMember: expanded.members?.length ? expanded.displayName : undefined,
  });
  return id;
}

export function getStashedFile(id: string): StashedFile | null {
  return stash.get(id) || null;
}

export function setActiveMember(id: string, memberName: string): StashedFile | null {
  const f = stash.get(id);
  if (!f?.members?.length) return f || null;
  const m = f.members.find((x) => x.name === memberName);
  if (!m) return f;
  f.blobUrl = m.blobUrl;
  f.filename = m.name;
  f.mime = m.mime;
  f.size = m.size;
  f.previewKind = m.previewKind;
  f.activeMember = m.name;
  return f;
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
  if (f.packageBlobUrl) {
    try {
      URL.revokeObjectURL(f.packageBlobUrl);
    } catch {
      /* ignore */
    }
  }
  for (const m of f.members || []) {
    try {
      if (m.blobUrl !== f.blobUrl) URL.revokeObjectURL(m.blobUrl);
    } catch {
      /* ignore */
    }
  }
  stash.delete(id);
}
