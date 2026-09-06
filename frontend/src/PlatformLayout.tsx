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
import { useEffect, useState } from 'react';
import './platform-layout.css';
import {
  ensurePwaInstallListener,
  getDeferredInstallPrompt,
  getLaunchAppMode,
  subscribePwaInstall,
} from './pwaInstall';

export interface PlatformUser {
  id?: string;
  name?: string;
  email?: string;
  tier?: 'free' | 'pro' | 'enterprise';
}

interface PlatformLayoutProps {
  children: React.ReactNode;
  user?: PlatformUser;
  onLogout?: () => void;
}

const PLATFORM_ROUTES = [
  {
    name: 'Home',
    path: '/',
    icon: Home,
    category: 'Main',
    description: 'RegGuard Site Diligence',
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
    description: 'Purchases and IC PDFs',
  },
  {
    name: 'Pricing',
    path: '/pricing',
    icon: DollarSign,
    category: 'Main',
    description: 'Plans and IC Project Report',
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

  // Hide desktop sidebar on public marketing home for unauthenticated users —
  // but always allow the mobile three-bar drawer (Launch app lives there).
  const isPublicPage = location.pathname === '/';
  const isAuthenticated = user?.email && user.email !== 'contractor@regguard.com';
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
      </div>

      {showSidebar && (
        <aside
          className={`platform-sidebar ${sidebarOpen ? 'open' : 'collapsed'} ${
            mobileMenuOpen ? 'mobile-open' : ''
          } ${!shouldShowDesktopSidebar ? 'mobile-only-sidebar' : ''}`}
        >
          <div className="sidebar-header">
            <Link to="/" className="platform-logo" onClick={() => setMobileMenuOpen(false)}>
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
                  return (
                    <Link
                      key={route.path}
                      to={route.path}
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
              <Link
                to="/install"
                className={`nav-item ${isActive('/install') ? 'active' : ''}`}
                title="Install or open Reg Guard as a phone app"
                onClick={() => setMobileMenuOpen(false)}
              >
                {launchMode === 'standalone' ? (
                  <Smartphone size={18} />
                ) : (
                  <Download size={18} />
                )}
                {(sidebarOpen || mobileMenuOpen) && (
                  <span className="nav-label">
                    {launchMode === 'standalone' ? 'Running as app' : 'Launch app'}
                  </span>
                )}
              </Link>
            </div>
          </nav>

          <div className="sidebar-footer">
            {user?.email && (sidebarOpen || mobileMenuOpen) && (
              <div className="user-info">
                <div className="user-avatar">
                  {user.name?.charAt(0).toUpperCase() || '?'}
                </div>
                <div>
                  <p className="user-name">{user.name || 'User'}</p>
                  <p className="user-email">{user.email}</p>
                </div>
              </div>
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
