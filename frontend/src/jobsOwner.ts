/**
 * Local identity for Saved Jobs (email + device owner_key).
 * Matches the Orders page pattern (email in sessionStorage).
 */

import { backendUrl } from './env';

const OWNER_KEY = 'regguard_owner_key';
const EMAIL_KEY = 'userEmail';

export function getOwnerKey(): string {
  if (typeof window === 'undefined') return '';
  let key = localStorage.getItem(OWNER_KEY);
  if (!key) {
    key =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? `own-${crypto.randomUUID()}`
        : `own-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(OWNER_KEY, key);
  }
  return key;
}

export function getJobsEmail(): string {
  if (typeof window === 'undefined') return '';
  return (sessionStorage.getItem(EMAIL_KEY) || localStorage.getItem('regguard_jobs_email') || '').trim();
}

export function setJobsEmail(email: string) {
  if (typeof window === 'undefined' || !email) return;
  const norm = email.trim().toLowerCase();
  if (!norm) return;
  sessionStorage.setItem(EMAIL_KEY, norm);
  localStorage.setItem('regguard_jobs_email', norm);
}

export async function persistSavedJob(input: {
  owner_email: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  project_type?: string;
  last_research_id?: string;
  share_url?: string;
  job_id?: string;
  phone?: string;
  last_stamp_grade?: string;
  punch_count?: number;
  preview?: boolean;
}): Promise<string | null> {
  const owner_email = (input.owner_email || '').trim().toLowerCase();
  const address = (input.address || '').trim();
  if (!owner_email || !address) return null;
  setJobsEmail(owner_email);
  try {
    const res = await fetch(backendUrl('/jobs'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner_email,
        owner_key: getOwnerKey(),
        address,
        city: input.city || '',
        state: input.state || '',
        zip: input.zip || '',
        project_type: input.project_type || 'general',
        last_research_id: input.last_research_id || '',
        share_url: input.share_url || '',
        job_id: input.job_id || undefined,
        phone: input.phone || '',
        summary_snapshot: {
          last_stamp_grade: input.last_stamp_grade || '',
          punch_count: input.punch_count ?? null,
          preview: Boolean(input.preview),
          regguard_stamp: input.last_stamp_grade ? { grade: input.last_stamp_grade } : undefined,
        },
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return null;
    const id = String((data.job && data.job.id) || '');
    if (id) {
      try {
        sessionStorage.setItem('lastJobId', id);
      } catch {
        /* ignore */
      }
    }
    return id || null;
  } catch {
    return null;
  }
}

export type SavedJob = {
  id: string;
  owner_email: string;
  owner_key?: string;
  address: string;
  city?: string;
  state?: string;
  zip?: string;
  project_type?: string;
  status?: string;
  last_research_id?: string;
  share_url?: string;
  last_run_at?: string;
  last_stamp_grade?: string;
  summary_snapshot?: {
    estimated_timeline?: string;
    estimated_total_cost?: number;
    risk_level?: string;
    preview?: boolean;
    punch_count?: number;
  };
  notes?: string;
  created_at?: string;
  updated_at?: string;
};
