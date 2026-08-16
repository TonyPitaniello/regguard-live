/**
 * Site binding helpers for IC auto-run after purchase.
 * Stripe metadata is source of truth; sessionStorage is a same-browser cache.
 */

export type BoundSite = {
  address: string;
  city: string;
  state: string;
  zip: string;
  projectType?: string;
  email?: string;
  label: string;
};

const PENDING_IC_TTL_MS = 2 * 60 * 60 * 1000; // 2h (premortem F9)

export function siteLabel(site: {
  address: string;
  city: string;
  state: string;
  zip: string;
}): string {
  return `${site.address}, ${site.city}, ${site.state} ${site.zip}`;
}

export function readLastResearchForm(): Partial<BoundSite> & {
  projectType?: string;
  email?: string;
} {
  try {
    const raw = sessionStorage.getItem('lastResearchForm');
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const address = typeof parsed.address === 'string' ? parsed.address : undefined;
    const city = typeof parsed.city === 'string' ? parsed.city : undefined;
    const state = typeof parsed.state === 'string' ? parsed.state : undefined;
    const zip = typeof parsed.zip === 'string' ? parsed.zip : undefined;
    return {
      address,
      city,
      state,
      zip,
      projectType: typeof parsed.projectType === 'string' ? parsed.projectType : undefined,
      email: typeof parsed.email === 'string' ? parsed.email : undefined,
      label:
        address && city && state && zip
          ? siteLabel({ address, city, state, zip })
          : undefined,
    };
  } catch {
    return {};
  }
}

export function persistLastResearchForm(data: {
  address: string;
  city: string;
  state: string;
  zip: string;
  projectType?: string;
  email?: string;
}): void {
  try {
    sessionStorage.setItem(
      'lastResearchForm',
      JSON.stringify({
        address: data.address,
        city: data.city,
        state: data.state,
        zip: data.zip,
        projectType: data.projectType || 'commercial',
        email: data.email || '',
      })
    );
  } catch {
    /* ignore */
  }
}

export function siteFromConfirmPayload(site: unknown, order?: unknown): BoundSite | null {
  const s = (site && typeof site === 'object' ? site : {}) as Record<string, unknown>;
  const o = (order && typeof order === 'object' ? order : {}) as Record<string, unknown>;
  const address = String(s.address || o.site_address || '').trim();
  const city = String(s.city || o.site_city || '').trim();
  const state = String(s.state || o.site_state || '').trim();
  const zip = String(s.zip || o.site_zip || '').trim();
  const projectType = String(s.project_type || o.site_project_type || 'commercial').trim();
  if (address && city && state && zip) {
    return {
      address,
      city,
      state,
      zip,
      projectType,
      label: String(s.label || o.site_label || siteLabel({ address, city, state, zip })),
    };
  }
  // Fallback: parse "street, city, state zip" from order.address / site_label
  const label = String(s.label || o.site_label || o.address || '').trim();
  if (!label) return null;
  const m = label.match(/^(.+),\s*([^,]+),\s*([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)\s*$/);
  if (!m) return null;
  return {
    address: m[1].trim(),
    city: m[2].trim(),
    state: m[3].trim().toUpperCase(),
    zip: m[4].trim(),
    projectType,
    label,
  };
}

export function setPendingIcReport(active: boolean): void {
  try {
    if (!active) {
      sessionStorage.removeItem('pendingIcReport');
      return;
    }
    sessionStorage.setItem(
      'pendingIcReport',
      JSON.stringify({ v: 1, ts: Date.now() })
    );
  } catch {
    /* ignore */
  }
}

/** True only when pendingIcReport is set and not older than 2h. */
export function hasValidPendingIcReport(): boolean {
  try {
    const raw = sessionStorage.getItem('pendingIcReport');
    if (!raw) return false;
    if (raw === '1') {
      // Legacy flag from older clients — accept once, rewrite with TTL
      setPendingIcReport(true);
      return true;
    }
    const parsed = JSON.parse(raw) as { v?: number; ts?: number };
    if (!parsed?.ts || Date.now() - parsed.ts > PENDING_IC_TTL_MS) {
      sessionStorage.removeItem('pendingIcReport');
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

export function clearPendingIcReport(): void {
  setPendingIcReport(false);
}

export function getOrCreateIcRunId(): string {
  try {
    const existing = sessionStorage.getItem('pendingIcRunId');
    if (existing) return existing;
    const id =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `ic-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    sessionStorage.setItem('pendingIcRunId', id);
    return id;
  } catch {
    return `ic-${Date.now()}`;
  }
}

export function clearIcRunId(): void {
  try {
    sessionStorage.removeItem('pendingIcRunId');
  } catch {
    /* ignore */
  }
}
