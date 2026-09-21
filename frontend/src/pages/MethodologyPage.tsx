/**
 * RegGuard How It Works — freemium preview + paid IC Diligence Bundle (honest)
 */

import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Shield, CheckCircle, Clock } from 'lucide-react';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';
import { IcDiligenceBundlePitch } from '../components/IcDiligenceBundlePitch';

export default function MethodologyPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        </div>
      </header>

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl font-black text-white mb-6">How RegGuard Works</h1>
          <p className="text-xl text-gray-300">
            Free: enter an address and get an instant Bid Risk Receipt preview in the app. Paid:
            Partner / Contractor Pro for bid-week habit, or the{' '}
            <span className="text-emerald-200 font-semibold">{IC_BUNDLE.productName}</span> — a
            counsel-ready ZIP (memo + DOCX + CSVs), not a longer PDF stack. Strongest citeable local
            depth today is Dallas, Plano, and Austin.
          </p>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-black text-white mb-8">Track A — Free preview (seconds)</h2>
          <div className="space-y-6">
            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-emerald-500/30 rounded-xl p-8">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0 text-white font-bold text-sm">
                  1
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white mb-2">Enter a site address</h3>
                  <p className="text-gray-300">
                    Street, city, state, ZIP. Optional map pin improves environmental GIS. No
                    credit card. Monthly free-lookup quota applies per email.
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-emerald-500/30 rounded-xl p-8">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0 text-white font-bold text-sm">
                  2
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white mb-2">Instant Bid Risk Receipt</h3>
                  <p className="text-gray-300 mb-3">
                    Ranked punch list (Critical → Low), coverage badge (full pack / portal /
                    federal-state), and planning contingency. Every line shows a source or{' '}
                    <strong className="text-amber-200">Unverified</strong>.
                  </p>
                  <p className="text-gray-400 text-sm">
                    Soft-locked lines unlock when you forward the receipt (SMS / email / copy) or
                    upgrade. Contingency is a planning aid — not a bid quote.
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-emerald-500/30 rounded-xl p-8">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0 text-white font-bold text-sm">
                  3
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white mb-2">Forward or upgrade</h3>
                  <p className="text-gray-300">
                    Text / email the receipt, deepen with Partner or Pro for bid week, or buy the{' '}
                    {IC_BUNDLE.productName} when counsel needs a citeable package for one site.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-black text-white mb-8">{IC_BUNDLE.methodologyTitle}</h2>
          <IcDiligenceBundlePitch className="mb-8" />
          <div className="space-y-6">
            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-purple-500/30 rounded-xl p-8">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0 text-white font-bold text-sm">
                  1
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white mb-2">Checkout via Stripe</h3>
                  <p className="text-gray-300">
                    {IC_BUNDLE.tierName} ({IC_BUNDLE.priceLabel} one-time) for one site&apos;s
                    Diligence Bundle. Address + project type bound to the order.
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-purple-500/30 rounded-xl p-8">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0 text-white font-bold text-sm">
                  2
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white mb-2">
                    {IC_BUNDLE.methodologyStep2Title}
                  </h3>
                  <p className="text-gray-300 mb-3">{IC_BUNDLE.readyBody}</p>
                  <ul className="text-gray-300 space-y-2 ml-1">
                    {IC_BUNDLE.contents.map((c) => (
                      <li key={c.file}>
                        <strong className="text-white">{c.label}</strong> — {c.detail}
                      </li>
                    ))}
                  </ul>
                  <p className="text-gray-400 text-sm mt-3">
                    Download the ZIP from IC-depth results. Optional longer boardroom PDF is
                    secondary. Parts may also appear under My Orders.
                  </p>
                </div>
              </div>
            </div>
          </div>
          <div className="mt-8 flex flex-col sm:flex-row gap-3">
            <button
              type="button"
              onClick={() => navigate('/checkout/ic_project')}
              className="px-6 py-3.5 min-h-[48px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl"
            >
              {IC_BUNDLE.ctaBuy}
            </button>
            <button
              type="button"
              onClick={() => navigate('/pricing')}
              className="px-6 py-3.5 min-h-[48px] border border-white/20 text-gray-200 font-semibold rounded-xl hover:bg-white/5"
            >
              Compare plans
            </button>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-black text-white mb-8">Expected timing</h2>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-emerald-500/30 rounded-xl p-6 text-center">
              <Clock className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
              <p className="text-sm font-bold text-white mb-2">Free preview</p>
              <p className="text-2xl font-black text-emerald-400">Seconds</p>
              <p className="text-xs text-gray-400 mt-2">In-app results modal</p>
            </div>
            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-blue-500/30 rounded-xl p-6 text-center">
              <Clock className="w-8 h-8 text-blue-400 mx-auto mb-2" />
              <p className="text-sm font-bold text-white mb-2">Partner / Pro deepen</p>
              <p className="text-2xl font-black text-blue-400">Minutes</p>
              <p className="text-xs text-gray-400 mt-2">Paid local confirm when available</p>
            </div>
            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-purple-500/30 rounded-xl p-6 text-center">
              <Clock className="w-8 h-8 text-purple-400 mx-auto mb-2" />
              <p className="text-sm font-bold text-white mb-2">{IC_BUNDLE.productName}</p>
              <p className="text-2xl font-black text-purple-400">Same day</p>
              <p className="text-xs text-gray-400 mt-2">ZIP after IC-depth lookup</p>
            </div>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-black text-white mb-8">What we guarantee (and what we don&apos;t)</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <CheckCircle className="w-6 h-6 text-green-400" />
                We guarantee
              </h3>
              <ul className="space-y-3 text-gray-300">
                <li className="flex gap-2">
                  <span className="text-green-400 font-bold">✓</span>
                  <span>Source link or honest Unverified on findings we show</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-green-400 font-bold">✓</span>
                  <span>Coverage honesty when local fees are not citeable yet</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-green-400 font-bold">✓</span>
                  <span>
                    Email support if a Critical SOURCE fee is wrong vs the official schedule that day
                    — we do not advertise a blanket 100% refund while /guarantee is empty
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-green-400 font-bold">✓</span>
                  <span>
                    IC Diligence Bundle ZIP structure (memo + counsel DOCX + CSVs + evidence) after
                    an IC-depth run
                  </span>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <span className="text-red-400 text-xl">✕</span>
                We don&apos;t guarantee
              </h3>
              <ul className="space-y-3 text-gray-300">
                <li className="flex gap-2">
                  <span className="text-red-400 font-bold">✕</span>
                  <span>Permit approval (only the AHJ decides)</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-red-400 font-bold">✕</span>
                  <span>Exact fees or contingency as a bid quote</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-red-400 font-bold">✕</span>
                  <span>Nationwide full-pack depth (DFW / Austin beachhead first)</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-red-400 font-bold">✕</span>
                  <span>Live RTO queue positions (demo tools are not product)</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-red-400 font-bold">✕</span>
                  <span>{IC_BUNDLE.notThis}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10">
        <div className="max-w-4xl mx-auto">
          <div className="bg-gradient-to-br from-blue-600/20 to-blue-700/10 border border-blue-500/30 rounded-xl p-8">
            <div className="flex items-start gap-4">
              <Shield className="w-6 h-6 text-blue-400 flex-shrink-0 mt-1" />
              <div>
                <h3 className="text-lg font-bold text-white mb-4">
                  Research tool — not legal advice
                </h3>
                <p className="text-gray-300 mb-4">
                  RegGuard outputs are planning aids. Have counsel and your engineer review before
                  you file or bid.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8 border-t border-purple-500/10 bg-slate-900/50">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-black text-white mb-6">Ready?</h2>
          <p className="text-gray-300 mb-8">
            Start with a free address lookup, or get the {IC_BUNDLE.productName} for counsel-ready
            site packages.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => navigate('/')}
              className="px-10 py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold text-lg rounded-xl transition shadow-lg shadow-green-500/30 cursor-pointer"
            >
              Free lookup
            </button>
            <button
              onClick={() => navigate('/checkout/ic_project')}
              className="px-10 py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-lg rounded-xl transition cursor-pointer"
            >
              {IC_BUNDLE.ctaBuy}
            </button>
            <button
              onClick={() => navigate('/pricing')}
              className="px-10 py-4 border border-purple-400/50 bg-slate-900/60 hover:bg-slate-800 text-white font-bold text-lg rounded-xl transition cursor-pointer"
            >
              View pricing
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
