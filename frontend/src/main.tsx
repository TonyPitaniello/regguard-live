import { createRoot } from 'react-dom/client';

import { AppRouter } from './AppRouter';
import { loadGoogleMapsApi } from './loadGoogleMaps';
import { ensurePwaInstallListener } from './pwaInstall';

import './index.css'; // Tailwind CSS + base styles
import 'react-toastify/dist/ReactToastify.css';
import './voice-command.css';
import './onboarding-system.css';
import './mobile-optimizations.css'; // Mobile performance optimization

// Capture install prompt as early as possible (before React mounts)
ensurePwaInstallListener();

// Render app immediately (don't block on Google Maps)
createRoot(document.getElementById('root')!).render(<AppRouter />);

// Load Google Maps API in background (non-blocking)
loadGoogleMapsApi().catch(err => console.warn('Google Maps failed (non-blocking):', err));
