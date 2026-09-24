/**
 * Reg Guard Landing Page — brand-first, estimator habit → IC after results.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle } from 'lucide-react';
import FreeTrialForm from '../components/FreeTrialForm';
import { SampleReportBlock } from '../components/SampleReportBlock';
import { backendUrl } from '../env';
import { SeoHead } from '../SeoHead';
import { oneClickInstallApp } from '../pwaInstall';
import { BRAND_LOCKUP, BRAND_PROSE, PRODUCT_COPY } from '../productCopy';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';
import { HABIT_TIERS } from '../habitDeliverableLadder';

export function PlatformDashboard() {
  const navigate = useNavigate();
  const [forwards, setForwards] = useState<number | null>(null);

  useEffect(() => {
    void fetch(backendUrl('/stats/forwards'))
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (typeof d?.forwards === 'number' && d.forwards > 0) setForwards(d.forwards);
      })
      .catch(() => undefined);
  }, []);

  const scrollToFreeTrial = () => {
    document.getElementById('free-trial-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleGetApp = () => {
    void oneClickInstallApp();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <SeoHead
        title={PRODUCT_COPY.seoTitle}
        description={PRODUCT_COPY.seoDescription}
        canonical="https://app.regguardagent.com/"
      />
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">{BRAND_LOCKUP}</h1>
          <div className="flex items-center gap-3 sm:gap-4">
            <button
              type="button"
              onClick={handleGetApp}
              className="text-emerald-300 hover:text-white transition text-sm font-bold min-h-[44px] px-2"
            >
              Download
            </button>
            <button
              type="button"
              onClick={() => navigate('/permit-fees')}
              className="hidden md:inline text-gray-300 hover:text-white transition text-sm font-semibold"
            >
              Cities
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
              {PRODUCT_COPY.navTryFree}
            </button>
          </div>
        </div>
      </header>

      <section className="px-4 pt-10 pb-4 sm:px-6 lg:px-8 sm:pt-14">
        <div className="max-w-2xl mx-auto text-center">
          <p className="text-5xl sm:text-6xl md:text-7xl font-black text-white mb-4 tracking-tight">
            {BRAND_LOCKUP}
          </p>
          <h2 className="text-xl sm:text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-300 to-green-400 mb-3">
            {PRODUCT_COPY.heroHeadline}
          </h2>
          <p className="text-gray-300 text-base sm:text-lg leading-relaxed max-w-xl mx-auto">
            {PRODUCT_COPY.heroSubhead}
          </p>
        </div>
      </section>

      <section className="px-3 pb-5 sm:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto rounded-2xl border border-emerald-500/30 bg-[rgba(15,29,56,0.95)] p-3.5 sm:p-6 shadow-lg shadow-black/20">
          <SampleReportBlock compact />
          <p className="text-center text-[#b8c1d1] text-xs mt-4 px-1">
            {PRODUCT_COPY.sampleBridge}
          </p>
        </div>
      </section>

      <section className="px-4 pb-6 sm:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto">
          <FreeTrialForm />
          <p className="text-center text-gray-400 text-sm mt-4">
            Built for commercial, industrial, and data-center-adjacent bids.
            {forwards != null && forwards > 0 ? (
              <>
                {' '}
                · {forwards.toLocaleString()}+ Bid Risk Receipts forwarded
              </>
            ) : null}
          </p>
        </div>
      </section>

      <section className="px-4 py-12 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-4xl mx-auto grid sm:grid-cols-3 gap-6 text-center">
          <div>
            <p className="text-3xl font-black text-emerald-400 mb-1">{HABIT_TIERS.free.priceLabel}</p>
            <p className="text-gray-400 text-sm">{PRODUCT_COPY.homePriceStrip.free}</p>
          </div>
          <div>
            <p className="text-3xl font-black text-white mb-1">{HABIT_TIERS.partner.priceLabel}/mo</p>
            <p className="text-gray-400 text-sm">{PRODUCT_COPY.homePriceStrip.partner}</p>
          </div>
          <div>
            <p className="text-3xl font-black text-white mb-1">{HABIT_TIERS.contractor_pro.priceLabel}/mo</p>
            <p className="text-gray-400 text-sm">{PRODUCT_COPY.homePriceStrip.pro}</p>
          </div>
        </div>
        <p className="text-center text-gray-500 text-sm mt-6">{PRODUCT_COPY.homePriceStrip.icAlso}</p>
        <div className="text-center mt-6">
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
                <h3 className="text-lg font-bold text-white mb-2">
                  Due diligence aid — independent verification required
                </h3>
                <p className="text-gray-300 text-sm sm:text-base">
                  {PRODUCT_COPY.honestyLong} Questions:{' '}
                  <a href="mailto:support@regguardagent.com" className="text-emerald-300 underline">
                    support@regguardagent.com
                  </a>
                  .
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
              onClick={() => navigate('/permit-fees')}
              className="text-purple-400 hover:text-purple-300 transition min-h-[44px]"
            >
              City permit pages
            </button>
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
            <button
              type="button"
              onClick={() => navigate('/sample-report')}
              className="text-purple-400 hover:text-purple-300 transition min-h-[44px]"
            >
              Sample results
            </button>
            <button
              type="button"
              onClick={() => navigate('/jobs')}
              className="text-purple-400 hover:text-purple-300 transition min-h-[44px]"
            >
              My Jobs
            </button>
            <a
              href="https://app.regguardagent.com/privacy"
              className="text-purple-400 hover:text-purple-300 transition inline-flex items-center min-h-[44px]"
            >
              Privacy Policy
            </a>
            <a
              href="https://app.regguardagent.com/terms"
              className="text-purple-400 hover:text-purple-300 transition inline-flex items-center min-h-[44px]"
            >
              Terms
            </a>
            <a
              href="mailto:support@regguardagent.com"
              className="text-purple-400 hover:text-purple-300 transition inline-flex items-center min-h-[44px]"
            >
              Contact
            </a>
          </div>
          <p className="text-xs">
            {BRAND_PROSE} © 2026 · Pitaniello Perkins LLC ·{' '}
            <a href="https://app.regguardagent.com/privacy" className="text-purple-400 hover:text-purple-300">
              Privacy Policy
            </a>
            {' · '}
            SMS: message frequency varies; message and data rates may apply. We do not share mobile
            numbers with third parties or affiliates for marketing. Reply STOP to opt out; HELP for
            help. Consent to SMS is not required to use {BRAND_PROSE}.
          </p>
          <p className="text-xs text-gray-500">
            {IC_BUNDLE.productName} ({IC_BUNDLE.priceLabel}/site) is on Pricing and in results after
            you run a site.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default PlatformDashboard;
