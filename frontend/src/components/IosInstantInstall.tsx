/**
 * iOS Home Screen helpers. Instruction UI removed — Download uses navigator.share only.
 */
import { isIosDevice, isStandaloneApp } from '../pwaInstall';

export async function openIosShareSheet(): Promise<'shared' | 'unsupported' | 'cancelled'> {
  if (typeof navigator === 'undefined' || typeof navigator.share !== 'function') {
    return 'unsupported';
  }
  try {
    await navigator.share({
      title: 'Reg Guard',
      text: 'Install Reg Guard',
      url: window.location.origin + '/',
    });
    return 'shared';
  } catch (err) {
    if (err && typeof err === 'object' && 'name' in err && (err as { name: string }).name === 'AbortError') {
      return 'cancelled';
    }
    return 'unsupported';
  }
}

/** No-op — instruction sheets removed. */
export function showIosInstallInstructions(): void {
  /* intentionally empty */
}

export async function instantIosInstall(): Promise<'shared' | 'unsupported' | 'cancelled' | 'skipped'> {
  if (!isIosDevice() || isStandaloneApp()) return 'skipped';
  const result = await openIosShareSheet();
  if (result === 'shared' || result === 'cancelled') return result;
  return 'unsupported';
}

/** No banner / steps UI. */
export default function IosInstantInstall() {
  return null;
}
