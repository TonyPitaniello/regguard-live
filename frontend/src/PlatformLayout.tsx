import { useLocation, Link, useNavigate } from 'react-router-dom';
import {
  Home,
  LogOut,
  ChevronRight,
  Menu,
  X,
  Briefcase,
  Download,
  Smartphone,
  DollarSign,
  BookOpen,
  Package,
} from 'lucide-react';
import { useEffect, useState, type MouseEvent } from 'react';
import './platform-layout.css';
import {
  ensurePwaInstallListener,
  getDeferredInstallPrompt,
  getLaunchAppMode,
  isStandaloneApp,
  oneClickInstallApp,
  subscribePwaInstall,
} from './pwaInstall';

export interface PlatformUser {
  id?: string;
  name?: string;
  email?: string;
  tier?: 'free' | 'pro' | 'enterprise';
}

/** Public support inbox — never use placeholder domains like contractor@regguard.com */
export const SUPPORT_EMAIL = 'support@regguardagent.com';

const PLACEHOLDER_EMAILS = new Set([
  'contractor@regguard.com',
  'contractor@regguardagent.com',
  'support@regguard.com', // wrong domain; real inbox is @regguardagent.com
]);

function isRealUserEmail(email?: string): boolean {
  const e = (email || '').trim().toLowerCase();
  return Boolean(e) && !PLACEHOLDER_EMAILS.has(e);
}

interface PlatformLayoutProps {
  children: React.ReactNode;
  user?: PlatformUser;
  onLogout?: () => void;
}

function homePathWithResume(): string {
  try {
    if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem('analysisResults')) {
      return '/?resume=1';
    }
  } catch {
    /* ignore */
  }
  return '/';
}

const PLATFORM_ROUTES = [
  {
    name: 'Home',
    path: '/',
    icon: Home,
    category: 'Main',
    description: 'Reg Guard Site Diligence Results',
  },
  {
    name: 'My Jobs',
    path: '/jobs',
    icon: Briefcase,
    category: 'Main',
    description: 'Saved site diligence',
  },
  {
    name: 'My Orders',
    path: '/orders',
    icon: Package,
    category: 'Main',
    description: 'Purchases and IC Diligence Bundle',
  },
  {
    name: 'Pricing',
    path: '/pricing',
    icon: DollarSign,
    category: 'Main',
    description: 'Plans and IC Diligence Bundle',
  },
  {
    name: 'How it works',
    path: '/how-it-works',
    icon: BookOpen,
    category: 'Main',
    description: 'Methodology',
  },
];

export function PlatformLayout({
  children,
  user,
  onLogout,
}: PlatformLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [launchMode, setLaunchMode] = useState(() => getLaunchAppMode());
  // Keep Get app visible in Safari tabs; only hide for real home-screen standalone.
  const showGetApp = !isStandaloneApp() && launchMode !== 'standalone';

  // Hide desktop sidebar on public marketing home for unauthenticated users —
  // but always allow the mobile three-bar drawer (Launch app lives there).
  const isPublicPage =
    location.pathname === '/' || location.pathname.startsWith('/view-file');
  const isAuthenticated = isRealUserEmail(user?.email);
  const shouldShowDesktopSidebar = !isPublicPage || Boolean(isAuthenticated);
  const showSidebar = shouldShowDesktopSidebar || mobileMenuOpen;

  useEffect(() => {
    ensurePwaInstallListener();
    const sync = () => {
      setLaunchMode(getLaunchAppMode());
      void getDeferredInstallPrompt();
    };
    sync();
    return subscribePwaInstall(sync);
  }, []);

  useEffect(() => {
    // Close drawer on navigation
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const isActive = (path: string) => {
    if (path === '/' && location.pathname === '/') return true;
    if (path === '/install' && (location.pathname === '/install' || location.pathname === '/launch')) {
      return true;
    }
    if (path !== '/' && location.pathname.startsWith(path)) return true;
    return false;
  };

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    }
    navigate('/');
  };

  const handleGetApp = (e: MouseEvent) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    void oneClickInstallApp();
  };

  const routesByCategory = PLATFORM_ROUTES.reduce(
    (acc, route) => {
      if (!acc[route.category]) {
        acc[route.category] = [];
      }
      acc[route.category].push(route);
      return acc;
    },
    {} as Record<string, typeof PLATFORM_ROUTES>
  );

  return (
    <div className="platform-layout">
      {/* Mobile Hamburger — always available */}
      <div className="mobile-menu-trigger">
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="hamburger-btn"
          aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
        <span className="mobile-menu-brand">Reg Guard</span>
        {showGetApp && (
          <button
            type="button"
            className="mobile-get-app"
            onClick={handleGetApp}
          >
            Download
          </button>
        )}
      </div>

      {showSidebar && (
        <aside
          className={`platform-sidebar ${sidebarOpen ? 'open' : 'collapsed'} ${
            mobileMenuOpen ? 'mobile-open' : ''
          } ${!shouldShowDesktopSidebar ? 'mobile-only-sidebar' : ''}`}
        >
          <div className="sidebar-header">
            <Link
              to={homePathWithResume()}
              className="platform-logo"
              onClick={() => setMobileMenuOpen(false)}
            >
              <div className="logo-mark">RG</div>
              <div className="logo-text">
                <h1>RegGuard</h1>
                <p>Platform</p>
              </div>
            </Link>
            <button
              type="button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="sidebar-toggle"
              title={sidebarOpen ? 'Collapse' : 'Expand'}
            >
              <ChevronRight size={18} />
            </button>
          </div>

          <nav className="sidebar-nav">
            {Object.entries(routesByCategory).map(([category, routes]) => (
              <div key={category} className="nav-section">
                <div className="nav-section-title">{category}</div>
                {routes.map((route) => {
                  const Icon = route.icon;
                  const active = isActive(route.path);
                  const to =
                    route.path === '/' ? homePathWithResume() : route.path;
                  return (
                    <Link
                      key={route.path}
                      to={to}
                      className={`nav-item ${active ? 'active' : ''}`}
                      title={route.description}
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <Icon size={18} />
                      {(sidebarOpen || mobileMenuOpen) && (
                        <>
                          <span className="nav-label">{route.name}</span>
                          {active && (
                            <span className="nav-indicator">
                              <div className="dot" />
                            </span>
                          )}
                        </>
                      )}
                    </Link>
                  );
                })}
              </div>
            ))}

            <div className="nav-section">
              <div className="nav-section-title">App</div>
              <button
                type="button"
                className={`nav-item ${isActive('/install') ? 'active' : ''}`}
                title="Download Reg Guard to your Home Screen"
                onClick={handleGetApp}
              >
                {showGetApp ? <Download size={18} /> : <Smartphone size={18} />}
                {(sidebarOpen || mobileMenuOpen) && (
                  <span className="nav-label">
                    {showGetApp ? 'Download app' : 'App help'}
                  </span>
                )}
              </button>
            </div>
          </nav>

          <div className="sidebar-footer">
            {isAuthenticated && (sidebarOpen || mobileMenuOpen) && (
              <div className="user-info">
                <div className="user-avatar">
                  {user?.name?.charAt(0).toUpperCase() || '?'}
                </div>
                <div>
                  <p className="user-name">{user?.name || 'User'}</p>
                  <p className="user-email">{user?.email}</p>
                </div>
              </div>
            )}
            {(sidebarOpen || mobileMenuOpen) && (
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                className="user-info"
                style={{ textDecoration: 'none', color: 'inherit' }}
                title="Email Reg Guard support"
              >
                <div className="user-avatar">S</div>
                <div>
                  <p className="user-name">Support</p>
                  <p className="user-email">{SUPPORT_EMAIL}</p>
                </div>
              </a>
            )}
            {isAuthenticated && (
              <button type="button" onClick={handleLogout} className="logout-btn">
                <LogOut size={16} />
                {(sidebarOpen || mobileMenuOpen) && <span>Sign Out</span>}
              </button>
            )}
          </div>
        </aside>
      )}

      <main
        className={`platform-main ${
          shouldShowDesktopSidebar && sidebarOpen ? '' : 'full-width'
        }`}
      >
        <div className="platform-content">{children}</div>
      </main>

      {mobileMenuOpen && (
        <div
          className="mobile-overlay"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden
        />
      )}
    </div>
  );
}
