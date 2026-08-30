import { backendUrl } from '../env';

/** Fire-and-forget product event for stamp funnel metrics. */
export function trackStampEvent(
  event: string,
  opts: {
    researchId?: string | null;
    zip?: string;
    stampGrade?: string;
    stampFingerprint?: string;
    channel?: string;
  } = {}
): void {
  try {
    void fetch(backendUrl('/events'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event,
        research_id: opts.researchId || '',
        zip_code: opts.zip || '',
        stamp_grade: opts.stampGrade || '',
        stamp_fingerprint: opts.stampFingerprint || '',
        channel: opts.channel || '',
      }),
      keepalive: true,
    });
  } catch {
    /* ignore */
  }
}
