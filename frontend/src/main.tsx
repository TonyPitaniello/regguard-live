import { createRoot } from 'react-dom/client';
import { registerSW } from 'virtual:pwa-register';

import { AppRouter } from './AppRouter';
import { ErrorBoundary } from './components/ErrorBoundary';
import { loadGoogleMapsApi } from './loadGoogleMaps';
import { ensurePwaInstallListener, markAppBootOk } from './pwaInstall';

import './index.css'; // Tailwind CSS + base styles
import 'react-toastify/dist/ReactToastify.css';
import './voice-command.css';
import './onboarding-system.css';
import './mobile-optimizations.css'; // Mobile performance optimization

// Capture install prompt as early as possible (before React mounts)
ensurePwaInstallListener();

// Keep installed / Launch-app clients on the latest build (avoid blank shells).
registerSW({
  immediate: true,
  onRegisteredSW(_swUrl, registration) {
    if (!registration) return;
    window.setInterval(() => {
      void registration.update();
    }, 60 * 60 * 1000);
  },
});

// Render app immediately (don't block on Google Maps)
createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <AppRouter />
  </ErrorBoundary>
);

markAppBootOk();

// Load Google Maps API in background (non-blocking)
loadGoogleMapsApi().catch(err => console.warn('Google Maps failed (non-blocking):', err));
