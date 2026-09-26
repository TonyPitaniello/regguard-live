/**
 * RegGuard Pricing — multi-segment business model
 * Contractor free / Pro, IC project / annual, Sponsor
 */

import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { Check, ArrowLeft } from 'lucide-react';
import { trackStampEvent } from '../lib/trackStampEvent';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';
import { IcDiligenceBundlePitch } from '../components/IcDiligenceBundlePitch';
import { SampleReportBlock } from '../components/SampleReportBlock';
import { HABIT_TIERS } from '../habitDeliverableLadder';

const TIERS = [
  {
    key: 'free',
    segment: 'Contractor',
    name: HABIT_TIERS.free.name,
    price: HABIT_TIERS.free.priceLabel,
    billing: HABIT_TIERS.free.billing,
    description: HABIT_TIERS.free.oneLiner,
    features: [...HABIT_TIERS.free.features],
    cta: 'Try Free',
    highlight: false,
  },
  {
    key: 'partner',
    segment: 'Estimator / Permit Runner',
    name: HABIT_TIERS.partner.name,
    price: HABIT_TIERS.partner.priceLabel,
    billing: HABIT_TIERS.partner.billing,
    description: HABIT_TIERS.partner.oneLiner,
    features: [...HABIT_TIERS.partner.features],
    cta: `Start ${HABIT_TIERS.partner.name} — $79/mo`,
    highlight: false,
  },
  {
    key: 'contractor_pro',
    segment: 'Contractor',
    name: HABIT_TIERS.contractor_pro.name,
    price: HABIT_TIERS.contractor_pro.priceLabel,
    billing: HABIT_TIERS.contractor_pro.billing,
    description: HABIT_TIERS.contractor_pro.oneLiner,
    features: [...HABIT_TIERS.contractor_pro.features],
    cta: 'Start Pro — $149/mo',
    highlight: true,
  },
  {
    key: 'ic_project',
    segment: IC_BUNDLE.segment,
    name: IC_BUNDLE.tierName,
    price: IC_BUNDLE.priceLabel,
    billing: IC_BUNDLE.billing,
    description: IC_BUNDLE.cardDescription,
    features: [...IC_BUNDLE.featureBullets],
    cta: IC_BUNDLE.ctaOrder,
    highlight: false,
  },
  {
    key: 'ic_annual',
    segment: IC_BUNDLE.segment,
    name: 'IC Annual',
    price: '$15,000',
    billing: 'per year',
    description: IC_BUNDLE.annualDescription,
    features: [...IC_BUNDLE.annualFeatures],
    cta: 'Subscribe Annually',
    highlight: false,
  },
] as const;

export default function PricingPage() {
  const navigate = useNavigate();

  useEffect(() => {
    trackStampEvent('pricing_view', { channel: 'pricing' });
  }, []);

  const handleCta = (tierKey: string) => {
    if (tierKey === 'free') {
      navigate('/');
      setTimeout(() => {
        document.getElementById('free-trial-form')?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      }, 100);
      return;
    }
    if (tierKey === 'sponsor') {
      window.location.href = 'mailto:support@regguardagent.com?subject=Reg%20Guard%20Partner%20sponsorship';
      return;
    }
    trackStampEvent('checkout_view', { channel: tierKey, meta: { tier: tierKey } });
    navigate(`/checkout/${tierKey}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <h1 className="text-xl font-black text-white">Pricing</h1>
          <div className="w-20" />
        </div>
      </header>

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-black text-white mb-6">Plans that match how you bid</h1>
          <p className="text-xl text-gray-300">
            Free Bid Risk Receipt preview → Estimator / Permit Runner or Contractor Pro for bid-week
            habit →{' '}
            <span className="text-emerald-200 font-semibold">{IC_BUNDLE.productName}</span> for
            counsel-ready site packages. Strongest coverage: Dallas / Plano / Austin / Fort Worth.
          </p>
        </div>
      </section>

      <section className="px-4 pb-10 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <IcDiligenceBundlePitch />
          <div className="mt-4 flex flex-col sm:flex-row gap-3 justify-center">
            <button
              type="button"
              onClick={() => handleCta('ic_project')}
              className="px-8 py-3.5 min-h-[48px] bg-emerald-600 hover:bg-emerald-500 text-white font-black rounded-xl transition shadow-lg shadow-emerald-500/20"
            >
              {IC_BUNDLE.ctaBuy}
            </button>
            <button
              type="button"
              onClick={() => handleCta('free')}
              className="px-6 py-3.5 min-h-[48px] border border-white/20 text-gray-200 font-semibold rounded-xl hover:bg-white/5"
            >
              Start with a free lookup
            </button>
          </div>
        </div>
      </section>

      <section className="px-4 pb-16 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto grid md:grid-cols-2 xl:grid-cols-3 gap-6">
          {TIERS.map((tier) => (
            <div
              key={tier.key}
              className={`bg-gradient-to-br from-slate-800/50 to-slate-900/50 rounded-2xl p-7 flex flex-col h-full border ${
                tier.highlight
                  ? 'border-2 border-emerald-500/60 shadow-lg shadow-emerald-500/10'
                  : 'border-purple-500/20'
              }`}
            >
              <p className="text-xs font-bold tracking-wide text-purple-300 mb-2">
                {tier.segment}
              </p>
              <h2 className="text-2xl font-black text-white mb-1">{tier.name}</h2>
              <p className="text-gray-400 text-sm mb-6">{tier.description}</p>

              <div className="mb-6">
                <div className="text-4xl font-black text-white">{tier.price}</div>
                <p className="text-gray-400 text-sm">{tier.billing}</p>
              </div>

              <ul className="space-y-3 mb-8 flex-grow">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3 text-gray-300 text-sm">
                    <Check className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleCta(tier.key)}
                className={`w-full px-6 py-3 font-bold rounded-lg transition cursor-pointer ${
                  tier.highlight
                    ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white shadow-lg shadow-green-500/20'
                    : 'border border-purple-500/50 hover:border-purple-500 text-white bg-slate-900/50 hover:bg-slate-900'
                }`}
              >
                {tier.cta}
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="px-4 py-12 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-3xl mx-auto">
          <h3 className="text-xl font-bold text-white mb-2 text-center">
            SAMPLE — same Fort Worth DC-adjacent site at every tier
          </h3>
          <p className="text-gray-400 text-sm mb-6 text-center">
            9999 Chapin School Road, Fort Worth, TX 76126 (labeled SAMPLE). Live Fort Worth AHJ
            cites. Tap View to open — Forward and Download are inside the viewer.
          </p>
          <SampleReportBlock compact />
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-3xl mx-auto">
          <div className="bg-gradient-to-br from-emerald-600/20 to-green-600/20 border-2 border-emerald-500/30 rounded-xl p-8">
            <h3 className="text-lg font-bold text-white mb-4">
              Due diligence aid — independent verification required
            </h3>
            <p className="text-gray-300">
              This is pre-bid research assistance, not a guarantee of fees, timelines, or AHJ
              approval. Confirm every item with the Authority Having Jurisdiction before you bid or
              file. Findings are labeled Source or Unverified. Questions:{' '}
              <a href="mailto:support@regguardagent.com" className="text-purple-300 underline">
                support@regguardagent.com
              </a>
              .
            </p>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-3xl mx-auto space-y-8">
          <h2 className="text-3xl font-black text-white">FAQ</h2>
          <div>
            <h3 className="text-lg font-bold text-white mb-2">What&apos;s free vs paid?</h3>
            <p className="text-gray-400">{IC_BUNDLE.faqWhatYouGet}</p>
            <p className="text-gray-400 mt-3">
              Free lookups are the lead magnet. Estimator / Permit Runner ($79/mo) is for permit
              runners and client-site screening. Contractor Pro ($149/mo) is for weekly bidders who
              need CSV + city pack. {IC_BUNDLE.productName} ({IC_BUNDLE.priceLabel}/site) is the
              counsel-ready ZIP.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white mb-2">
              What exactly is in the $1,500 IC Diligence Bundle?
            </h3>
            <p className="text-gray-400">{IC_BUNDLE.oneLiner}</p>
            <ul className="mt-3 space-y-2 text-gray-400 text-sm">
              {IC_BUNDLE.contents.map((c) => (
                <li key={c.file}>
                  <span className="text-white font-semibold">{c.label}</span> — {c.detail}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white mb-2">Can I buy just one IC report?</h3>
            <p className="text-gray-400">
              Yes. Choose {IC_BUNDLE.tierName} at {IC_BUNDLE.priceLabel} one-time for one site&apos;s{' '}
              {IC_BUNDLE.productName} ZIP. After that first Project, IC Annual ($15,000/year) covers
              the same counsel ZIP for more bound capital sites on this purchase email — ahead of
              Project rate once you pass roughly ten sites. Built for deal-ready IC / lender
              packages, not day-to-day Contractor Pro lookups.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white mb-2">Where does coverage work best?</h3>
            <p className="text-gray-400">
              Strongest citeable coverage today:{' '}
              <button
                type="button"
                className="text-purple-300 hover:text-white underline"
                onClick={() => navigate('/plano-permit-fees')}
              >
                Plano
              </button>
              ,{' '}
              <button
                type="button"
                className="text-purple-300 hover:text-white underline"
                onClick={() => navigate('/dallas-permit-fees')}
              >
                Dallas
              </button>
              ,{' '}
              <button
                type="button"
                className="text-purple-300 hover:text-white underline"
                onClick={() => navigate('/austin-permit-fees')}
              >
                Austin
              </button>
              . Outside those AHJs, expect more Unverified lines.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white mb-2">Do you offer refunds?</h3>
            <p className="text-gray-400">
              Refund window and honest labeling: planning aids with Source / Unverified. We do not
              invent fees or claim sealed-bid / interconnection / geotech completeness.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white mb-2">Is the IC Queue / RTO tracker live?</h3>
            <p className="text-gray-400">
              No. Interconnection queue tools are demo-only and disabled in production. Buy the{' '}
              {IC_BUNDLE.productName} for citeable site diligence (ZIP: decision memo + boardroom PDF
              + counsel DOCX + estimator Excel) — not live RTO queue positions.
            </p>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10 bg-slate-900/50">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-black text-white mb-6">Not sure which plan?</h2>
          <p className="text-gray-300 mb-8">Start free, then upgrade when you need a full package.</p>
          <button
            onClick={() => handleCta('free')}
            className="px-10 py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold text-lg rounded-xl transition shadow-lg shadow-green-500/30 cursor-pointer"
          >
            Try Free Lookup
          </button>
          <p className="text-gray-400 text-sm mt-6">
            Questions?{' '}
            <a href="mailto:support@regguardagent.com" className="text-purple-400 hover:text-purple-300">
              support@regguardagent.com
            </a>
          </p>
        </div>
      </section>
    </div>
  );
}
