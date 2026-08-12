/**
 * RegGuard Pricing — multi-segment business model
 * Contractor free / Pro, IC project / annual, Sponsor
 */

import { useNavigate } from 'react-router-dom';
import { Check, ArrowLeft, Download } from 'lucide-react';
import { backendUrl } from '../env';

const TIERS = [
  {
    key: 'free',
    segment: 'Contractor',
    name: 'Free Lookups',
    price: '$0',
    billing: 'Free lead magnet',
    description:
      'DFW/Austin-first punch list preview. Source or Unverified on every line. Forward to unlock more.',
    features: [
      'Free site diligence lookup',
      'Top punch-list actions (soft-locked preview)',
      'Forward punch list to unlock full free list',
      'Text or email your results',
    ],
    cta: 'Try Free',
    highlight: false,
  },
  {
    key: 'partner',
    segment: 'Partner',
    name: 'Partner / Permit Runner',
    price: '$79',
    billing: 'per month',
    description:
      'For estimators and permit runners who screen sites for clients and share RegGuard.',
    features: [
      'Deep research lookups for client sites',
      'Forwardable punch lists with your workflow',
      'Saved Jobs + weekly email reminders',
      'Affiliate referral link (20% commission)',
    ],
    cta: 'Start Partner — $79/mo',
    highlight: false,
  },
  {
    key: 'contractor_pro',
    segment: 'Contractor',
    name: 'Contractor Pro',
    price: '$149',
    billing: 'per month',
    description: 'For contractors who screen DFW/Austin sites weekly.',
    features: [
      'Deep scout research on every lookup',
      'Full punch lists, costs & action plans',
      'Unlock deeper results after free preview',
      'Strongest citeable coverage: Dallas / Plano / Austin',
    ],
    cta: 'Start Pro',
    highlight: true,
  },
  {
    key: 'ic_project',
    segment: 'IC Consultant',
    name: 'IC Project Report',
    price: '$1,500',
    billing: 'one-time per project',
    description:
      'Planning diligence PDF package for one site (not an official AHJ filing).',
    features: [
      'Research memo (PDF)',
      'Contractor punch list (PDF)',
      'Permit package worksheet (PDF)',
      'Strongest citeable coverage: Dallas / Plano / Austin TX',
      'Generated after a confirmed site lookup',
    ],
    cta: 'Order Report',
    highlight: false,
  },
  {
    key: 'ic_annual',
    segment: 'IC Consultant',
    name: 'IC Annual',
    price: '$15,000',
    billing: 'per year',
    description:
      'Annual access to regenerate IC Project Report PDFs for additional sites.',
    features: [
      'Regenerate reports for new site addresses',
      'Same memo + punch list + permit worksheet package',
      'Strongest citeable coverage: Dallas / Plano / Austin TX',
      'Email support via support@regguardagent.com',
    ],
    cta: 'Subscribe Annually',
    highlight: false,
  },
  {
    key: 'sponsor',
    segment: 'Sponsor',
    name: 'Sponsor',
    price: '$1,500',
    billing: 'per month',
    description: 'Brand sponsorship for utilities, platforms, and partners.',
    features: [
      'Sponsored placement & co-branding',
      'Lead sharing options',
      'Monthly reporting',
      'Partner success manager',
    ],
    cta: 'Become a Sponsor',
    highlight: false,
  },
] as const;

export default function PricingPage() {
  const navigate = useNavigate();

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
            Reverse-benchmark pricing: free citeable punch list → Pro deep research → IC PDFs.
            Beachhead: Dallas / Plano / Austin.
          </p>
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
              <p className="text-xs font-bold uppercase tracking-wider text-purple-300 mb-2">
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
        <div className="max-w-3xl mx-auto text-center">
          <h3 className="text-xl font-bold text-white mb-3">See a SAMPLE Plano punch list</h3>
          <p className="text-gray-400 text-sm mb-6">
            Labeled SAMPLE PDF — fictional Plano address for buyers. Not a live site report.
          </p>
          <a
            href={backendUrl('/sample/plano-punch-list.pdf')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/15 border border-purple-400/40 text-white font-semibold rounded-xl transition min-h-[44px]"
            target="_blank"
            rel="noreferrer"
          >
            <Download className="w-4 h-4" />
            Download SAMPLE Plano PDF
          </a>
          <p className="mt-4">
            <button
              type="button"
              onClick={() => navigate('/affiliate')}
              className="text-purple-300 hover:text-white text-sm font-semibold min-h-[44px]"
            >
              Earn 20% with a referral link →
            </button>
          </p>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-3xl mx-auto">
          <div className="bg-gradient-to-br from-emerald-600/20 to-green-600/20 border-2 border-emerald-500/30 rounded-xl p-8">
            <h3 className="text-lg font-bold text-white mb-4">Our Accuracy Guarantee</h3>
            <p className="text-gray-300">
              If a critical finding is wrong, we refund 100% of your payment. No questions asked.
            </p>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-3xl mx-auto space-y-8">
          <h2 className="text-3xl font-black text-white">FAQ</h2>
          <div>
            <h3 className="text-lg font-bold text-white mb-2">What&apos;s free vs paid?</h3>
            <p className="text-gray-400">
              Free lookups are the lead magnet — summary results in-app. Contractor Pro ($149/mo)
              unlocks ongoing use. IC Project ($1,500) is a one-time full report package.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white mb-2">Can I buy just one IC report?</h3>
            <p className="text-gray-400">
              Yes. Choose IC Project Report at $1,500 one-time. High-volume practices usually prefer
              IC Annual at $15,000/year.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white mb-2">Do you offer refunds?</h3>
            <p className="text-gray-400">
              Yes. 7-day refund if you&apos;re unsatisfied, plus our accuracy guarantee on critical findings.
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
            <a href="mailto:hello@regguard.com" className="text-purple-400 hover:text-purple-300">
              hello@regguard.com
            </a>
          </p>
        </div>
      </section>
    </div>
  );
}
