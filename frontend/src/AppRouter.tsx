import { BrowserRouter as Router, Routes, Route, Link, Navigate, useSearchParams } from 'react-router-dom';
import { useEffect, useState, type ReactNode } from 'react';
import App from './App';
import { DataCenterRequestForm } from './DataCenterRequestForm';
import { DataCenterHub } from './pages/DataCenterHub';
import FreeTrialForm from './components/FreeTrialForm';
import { SalesLeadsDashboard } from './SalesLeadsDashboard';
import { QueueLanding } from './Queue/QueueLanding';
import { QueueUploadForm } from './Queue/QueueUploadForm';
import QueueMonitorDashboard from './Queue/QueueMonitorDashboard';
import StudyTranslator from './Queue/StudyTranslator';
import TimelinePredictor from './Queue/TimelinePredictor';
import { PlatformLayout, PlatformUser } from './PlatformLayout';
import PlatformDashboard from './pages/MergedDashboard';
import SignupPage from './pages/SignupPage';
import PricingPage from './pages/PricingPage';
import MethodologyPage from './pages/MethodologyPage';
import FreeTrialPage from './pages/FreeTrialPage';
import ResultsPage from './pages/ResultsPage';
import SharedReportPage from './pages/SharedReportPage';
import JobsPage from './pages/JobsPage';
import SampleReportPage from './pages/SampleReportPage';
import PremiumCheckoutPage from './pages/PremiumCheckoutPage';
import OrdersPage from './pages/OrdersPage';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';
import TermsOfServicePage from './pages/TermsOfServicePage';
import AffiliatePage from './pages/AffiliatePage';
import GeoPermitLandingPage from './pages/GeoPermitLandingPage';
import VoiceCommandSystem from './VoiceCommandSystem';
import OnboardingSystem from './OnboardingSystem';
import PwaInstallBanner from './components/PwaInstallBanner';
import { backendUrl, isIcDemoEnabled } from './env';
import './router-layout.css';

function IcDemoWatermark({ children }: { children: ReactNode }) {
  return (
    <div className="relative">
      <div
        className="sticky top-0 z-40 border-b border-amber-500/50 bg-amber-500 text-slate-950 px-4 py-2 text-center text-sm font-bold"
        role="status"
      >
        DEMO ONLY — NOT LIVE RTO / QUEUE DATA. Do not use for investment or interconnection decisions.
        {!isIcDemoEnabled() ? ' (Routes disabled in production.)' : ''}
      </div>
      {children}
    </div>
  );
}

function IcDemoDisabledPage() {
  return (
    <div className="max-w-xl mx-auto my-16 px-4 text-center space-y-4">
      <h1 className="text-2xl font-black text-white">IC Queue demo is offline</h1>
      <p className="text-gray-300 text-sm leading-relaxed">
        RegGuard’s interconnection queue tools currently return synthetic demo data.
        They are disabled in production so contractors and IC buyers are not shown
        fabricated queue positions or study costs.
      </p>
      <p className="text-gray-400 text-xs">
        Operators can enable the demo with <code className="text-amber-200">VITE_REG_GUARD_IC_DEMO=1</code> and{' '}
        <code className="text-amber-200">REG_GUARD_IC_DEMO=1</code> for pitch environments only.
      </p>
      <Link
        to="/"
        className="inline-flex items-center justify-center rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-500"
      >
        Back to home
      </Link>
    </div>
  );
}

/** Capture ?ref= into sessionStorage and ping affiliate click (once). */
function ReferralCapture() {
  const [params] = useSearchParams();
  useEffect(() => {
    const ref = (params.get('ref') || '').trim().toLowerCase();
    if (!ref) return;
    try {
      sessionStorage.setItem('referralCode', ref);
      localStorage.setItem('referralCode', ref);
    } catch {
      /* ignore */
    }
    fetch(backendUrl(`/affiliates/click?code=${encodeURIComponent(ref)}`), {
      method: 'POST',
    }).catch(() => undefined);
  }, [params]);
  return null;
}


export function AppRouter() {
  // Force rebuild - v4 with all critical UI/UX fixes
  console.log('✅ AppRouter rendering - Clean landing page, no sidebar on /');
  
  // Simulated user (in production, this comes from auth context)
  const [user] = useState<PlatformUser>({
    name: 'Contractor',
    email: 'contractor@regguard.com',
    tier: 'pro',
  });

  const handleLogout = () => {
    console.log('User logged out');
  };

  return (
    <Router>
      <PlatformLayout user={user} onLogout={handleLogout}>
        <ReferralCapture />
        <OnboardingSystem />
        <VoiceCommandSystem />
        <PwaInstallBanner />
        
        <Routes>
          {/* Home Dashboard */}
          <Route path="/" element={<PlatformDashboard />} />

          {/* Pricing */}
          <Route path="/pricing" element={<PricingPage />} />

          {/* GEO beachhead landings → free tool */}
          <Route path="/plano-permit-fees" element={<GeoPermitLandingPage />} />
          <Route path="/dallas-permit-fees" element={<GeoPermitLandingPage />} />
          <Route path="/austin-permit-fees" element={<GeoPermitLandingPage />} />

          {/* Methodology & Trust */}
          <Route path="/methodology" element={<MethodologyPage />} />
          <Route path="/how-it-works" element={<MethodologyPage />} />
          <Route path="/privacy" element={<PrivacyPolicyPage />} />
          <Route path="/terms" element={<TermsOfServicePage />} />

          {/* Free Trial */}
          <Route path="/free-trial" element={<FreeTrialPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/r/:id" element={<SharedReportPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/my-jobs" element={<JobsPage />} />
          
          {/* Orders and Payment */}
          <Route path="/order" element={<PremiumCheckoutPage />} />
          <Route path="/checkout/:tier" element={<PremiumCheckoutPage />} />
          <Route path="/checkout" element={<PremiumCheckoutPage />} />
          <Route path="/checkout/success" element={<OrdersPage />} />
          <Route path="/orders" element={<OrdersPage />} />

          {/* Sample Report */}
          <Route path="/sample-report" element={<SampleReportPage />} />

          {/* Affiliate */}
          <Route path="/affiliate" element={<AffiliatePage />} />
          <Route path="/partner" element={<AffiliatePage />} />

          {/* Signup/Stripe Payment Page */}
          <Route path="/signup" element={<SignupPage />} />

          {/* RegGuard Queue Routes — gated; demo data only when explicitly enabled */}
          <Route
            path="/queue"
            element={isIcDemoEnabled() ? <QueueLandingPage /> : <IcDemoDisabledPage />}
          />
          <Route
            path="/queue/upload"
            element={isIcDemoEnabled() ? <QueueUploadPage /> : <IcDemoDisabledPage />}
          />
          <Route
            path="/queue/monitor"
            element={isIcDemoEnabled() ? <QueueMonitorPage /> : <IcDemoDisabledPage />}
          />
          <Route
            path="/queue/translator"
            element={isIcDemoEnabled() ? <TranslatorPage /> : <IcDemoDisabledPage />}
          />
          <Route
            path="/queue/timeline"
            element={isIcDemoEnabled() ? <TimelinePage /> : <IcDemoDisabledPage />}
          />

          {/* Data Center B2B Routes */}
          <Route path="/data-center" element={<DataCenterPage />} />
          <Route path="/admin/leads" element={<AdminLeadsPage />} />

          {/* Existing Compliance Routes */}
          <Route path="/agent" element={<App />} />
          <Route path="/dashboard" element={<App />} />
          <Route path="/auth/success" element={<App />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </PlatformLayout>
    </Router>
  );
}

function DataCenterPage() {
  return (
    <div className="min-h-screen bg-slate-950">
      <DataCenterHub />
      <section className="px-4 py-12 sm:px-6 lg:px-8 border-t border-indigo-500/20">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-2 text-center">
            Run a TX data-center site lookup
          </h2>
          <p className="text-gray-400 text-sm text-center mb-6">
            Parallel-track Bid Risk Receipt — AHJ + utility risk before bid. Not an
            interconnection study or AHJ filing.
          </p>
          <FreeTrialForm defaultProjectType="data-center" lockProjectType />
        </div>
      </section>
      <section className="px-4 py-10 sm:px-6 lg:px-8 bg-slate-900/50">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-xl font-bold text-white mb-2 text-center">
            Or request a deeper IC-style review
          </h2>
          <p className="text-gray-400 text-sm text-center mb-6">
            Lead form for larger colo / large-load diligence conversations ($1,500 IC
            Project path).
          </p>
          <DataCenterRequestForm />
        </div>
      </section>
    </div>
  );
}

function QueueLandingPage() {
  return (
    <IcDemoWatermark>
      <QueueLanding />
    </IcDemoWatermark>
  );
}

function QueueMonitorPage() {
  return (
    <IcDemoWatermark>
      <div>
        <div className="page-header">
          <div className="page-title">
            <h1>Queue Monitor</h1>
            <p>Track your RTO queue position</p>
          </div>
        </div>
        <QueueMonitorDashboard />
      </div>
    </IcDemoWatermark>
  );
}

function TranslatorPage() {
  return (
    <IcDemoWatermark>
      <div>
        <div className="page-header">
          <div className="page-title">
            <h1>Study Translator</h1>
            <p>Extract interconnection study metrics</p>
          </div>
        </div>
        <StudyTranslator />
      </div>
    </IcDemoWatermark>
  );
}

function TimelinePage() {
  return (
    <IcDemoWatermark>
      <div>
        <div className="page-header">
          <div className="page-title">
            <h1>Timeline Predictor</h1>
            <p>Estimate your project energization date</p>
          </div>
        </div>
        <TimelinePredictor />
      </div>
    </IcDemoWatermark>
  );
}

function QueueUploadPage() {
  return (
    <IcDemoWatermark>
      <div>
        <div className="page-header">
          <div className="page-title">
            <h1>Upload Interconnection Study</h1>
            <p>Extract key metrics and auto-fill forms</p>
          </div>
        </div>
        <QueueUploadForm />
      </div>
    </IcDemoWatermark>
  );
}

function AdminLeadsPage() {
  return (
    <div>
      <div className="page-header">
        <div className="page-title">
          <h1>Sales Pipeline</h1>
          <p>Data Center Analysis Leads</p>
        </div>
      </div>
      <SalesLeadsDashboard backendUrl={backendUrl('')} />
    </div>
  );
}