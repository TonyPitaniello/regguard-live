/**
 * Soft navigation bridge so non-React modules (pdfExport) can open routes.
 */

import type { NavigateFunction } from 'react-router-dom';

let navigateRef: NavigateFunction | null = null;

export function setAppNavigate(navigate: NavigateFunction | null): void {
  navigateRef = navigate;
}

export function appNavigate(to: string): void {
  if (navigateRef) {
    navigateRef(to);
    return;
  }
  // Fallback if bridge not ready yet
  try {
    window.location.assign(to);
  } catch {
    /* ignore */
  }
}
