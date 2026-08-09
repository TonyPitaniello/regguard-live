/**
 * RegGuard Landing Page — viral, brand-first, one job: site research fast.
 * Dark purple / slate / green aesthetic preserved.
 */

import { useNavigate } from 'react-router-dom';
import { CheckCircle } from 'lucide-react';
import FreeTrialForm from '../components/FreeTrialForm';

export function PlatformDashboard() {
  const navigate = useNavigate();

  const scrollToFreeTrial = () => {
    document.getElementById('free-trial-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">RegGuard</h1>
          <div className="flex items-center gap-3 sm:gap-4">
            <button
              type="button"
              onClick={() => navigate('/jobs')}
              className="hidden sm:inline text-gray-300 hover:text-white transition text-sm font-semibold"
            >
              My Jobs
            </button>
            <button
              type="button"
              onClick={() => navigate('/how-it-works')}
              className="hidden sm:inline text-gray-300 hover:text-white transition text-sm font-semibold"
            >
              How it works
            </button>
            <button
              type="button"
              onClick={() => navigate('/pricing')}
              className="text-gray-300 hover:text-white transition text-sm font-semibold min-h-[44px] px-2"
            >
              Pricing
            </button>
            <button
              type="button"
              onClick={scrollToFreeTrial}
              className="px-4 sm:px-5 py-2.5 min-h-[44px] bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold rounded-lg transition shadow-lg shadow-green-500/20 cursor-pointer text-sm"
            >
              Try free
            </button>
          </div>
        </div>
      </header>

      {/* Hero: brand + one line + form (the only CTA) */}
      <section className="px-4 pt-10 pb-6 sm:px-6 lg:px-8 sm:pt-14">
        <div className="max-w-2xl mx-auto text-center mb-8">
          <p className="text-5xl sm:text-6xl md:text-7xl font-black text-white mb-4 tracking-tight">
            RegGuard
          </p>
          <h2 className="text-xl sm:text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-300 to-green-400 mb-3">
            Pre-bid site diligence — in seconds
          </h2>
          <p className="text-gray-300 text-base sm:text-lg leading-relaxed max-w-xl mx-auto">
            Enter an address. RegGuard pulls local permitting rules, key state/federal flags, and a contractor punch list you can forward — no credit card.
          </p>
        </div>

        <div className="max-w-2xl mx-auto">
          <FreeTrialForm />
          <p className="text-center text-gray-400 text-sm mt-4">
            Works for commercial, industrial, data centers, solar/battery, and utility projects.
          </p>
        </div>
      </section>

      <section className="px-4 py-12 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-3xl mx-auto grid sm:grid-cols-3 gap-6 text-center">
          <div>
            <p className="text-3xl font-black text-emerald-400 mb-1">$0</p>
            <p className="text-gray-400 text-sm">Free lookup — results in-app</p>
          </div>
          <div>
            <p className="text-3xl font-black text-white mb-1">$149/mo</p>
            <p className="text-gray-400 text-sm">Contractor Pro</p>
          </div>
          <div>
            <p className="text-3xl font-black text-white mb-1">$1,500</p>
            <p className="text-gray-400 text-sm">IC Project Report</p>
          </div>
        </div>
        <div className="text-center mt-8">
          <button
            type="button"
            onClick={() => navigate('/pricing')}
            className="text-purple-300 hover:text-white font-semibold transition min-h-[44px]"
          >
            Full pricing →
          </button>
        </div>
      </section>

      <section className="px-4 py-12 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-3xl mx-auto">
          <div className="bg-gradient-to-br from-emerald-600/20 to-green-600/20 border border-emerald-500/30 rounded-xl p-6 sm:p-8">
            <div className="flex items-start gap-4">
              <CheckCircle className="w-7 h-7 text-emerald-400 flex-shrink-0 mt-1" />
              <div>
                <h3 className="text-lg font-bold text-white mb-2">Guarantee</h3>
                <p className="text-gray-300 text-sm sm:text-base">
                  If a critical paid finding is wrong, we refund 100%. Free lookups always show an in-app
                  preview so you can text or share immediately.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="px-4 py-10 sm:px-6 lg:px-8 bg-slate-900/50 border-t border-purple-500/10 text-center text-gray-400 text-sm">
        <div className="max-w-6xl mx-auto space-y-3">
          <div className="flex justify-center gap-6 flex-wrap">
            <button
              type="button"
              onClick={() => navigate('/how-it-works')}
              className="text-purple-400 hover:text-purple-300 transition min-h-[44px]"
            >
              How it works
            </button>
            <button
              type="button"
              onClick={() => navigate('/pricing')}
              className="text-purple-400 hover:text-purple-300 transition min-h-[44px]"
            >
              Pricing
            </button>
            <a
              href="mailto:hello@regguard.com"
              className="text-purple-400 hover:text-purple-300 transition inline-flex items-center min-h-[44px]"
            >
              Contact
            </a>
          </div>
          <p className="text-xs">RegGuard © 2026 · Permitting research intelligence</p>
        </div>
      </footer>
    </div>
  );
}

export default PlatformDashboard;
