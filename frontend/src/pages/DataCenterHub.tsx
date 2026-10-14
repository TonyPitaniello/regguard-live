/**
 * RegGuard Data Center Hub.
 * Paid plans go to Stripe checkout. Free starts a site lookup. No card fields on this page.
 */

import {
  Zap,
  MapPin,
  Clock,
  DollarSign,
  CheckCircle,
  AlertTriangle,
  FileText,
  Users,
  Shield,
  BookOpen,
  ArrowRight,
  Lock,
  Gauge,
  Workflow
} from 'lucide-react';
import { IC_BUNDLE } from '../icDiligenceBundleCopy';
import { HABIT_TIERS } from '../habitDeliverableLadder';
import { IcDiligenceBundlePitch } from '../components/IcDiligenceBundlePitch';

interface DataCenterCapability {
  icon: React.ReactNode;
  title: string;
  description: string;
  status: 'ready' | 'beta' | 'coming';
  value: string;
}

export function DataCenterHub() {

  // === PRIMARY: Data Center Capabilities ===
  const dataCenterCapabilities: DataCenterCapability[] = [
    {
      icon: <Zap className="w-6 h-6" />,
      title: 'Parallel-clock Bid Risk Receipt',
      description: 'AHJ vs utility vs FAST-41 tracks on one forwardable receipt — not an interconnect study',
      status: 'ready',
      value: '$0'
    },
    {
      icon: <MapPin className="w-6 h-6" />,
      title: 'Moratorium / pause radar',
      description: 'Seeded metro watchlist (VA/OH/GA/OK/NY/TX/AZ/WA/IL) + scout hits — verify with counsel',
      status: 'ready',
      value: 'API'
    },
    {
      icon: <Clock className="w-6 h-6" />,
      title: 'Power path honesty pack',
      description: 'Study-type checklist + surcharge band labeled planning-only — no fake MW available',
      status: 'ready',
      value: '$0'
    },
    {
      icon: <AlertTriangle className="w-6 h-6" />,
      title: 'Water, opposition & FAST-41 cards',
      description: 'Cooling constraints, community friction, federal gate clarity on every DC run',
      status: 'ready',
      value: '$0'
    },
    {
      icon: <FileText className="w-6 h-6" />,
      title: 'War-room share + diligence export',
      description: 'Multiplayer comments on /r/{id} + JSON export for CRM/GIS (regguard.dc_diligence.v1)',
      status: 'ready',
      value: 'API'
    },
    {
      icon: <DollarSign className="w-6 h-6" />,
      title: 'ZIP watch (DC fingerprints)',
      description: 'Pack + moratorium radar changes page saved ZIPs — schedule /cron/zip-watch',
      status: 'beta',
      value: 'Cron'
    }
  ];

  // === SECONDARY: Other Capabilities ===
  const otherCapabilities = [
    { icon: <Users className="w-5 h-5" />, title: 'Saved jobs', desc: 'Jobs and orders stay in your account so you can reopen a site' },
    { icon: <BookOpen className="w-5 h-5" />, title: 'Regulatory research', desc: 'AHJ and utility screening with Source or Unverified on each line' },
    { icon: <Gauge className="w-5 h-5" />, title: 'Bid Risk Receipt', desc: 'Forwardable planning aid — confirm fees and clocks with the AHJ' },
    { icon: <Workflow className="w-5 h-5" />, title: 'Permit worksheets', desc: 'Draft forms you fill and file — not a sealed bid or interconnection study' },
  ];

  const pricingPlans: Array<{
    name: string;
    price: string;
    period: string;
    features: readonly string[];
    href: string;
    cta: string;
    recommended?: boolean;
  }> = [
    {
      name: HABIT_TIERS.free.name,
      price: HABIT_TIERS.free.priceLabel,
      period: 'no card',
      features: HABIT_TIERS.free.features,
      href: '/data-center#free-trial-form',
      cta: 'Run a free lookup',
    },
    {
      name: HABIT_TIERS.partner.name,
      price: HABIT_TIERS.partner.priceLabel,
      period: 'month',
      features: HABIT_TIERS.partner.features,
      href: '/checkout/partner',
      cta: 'Start Estimator',
    },
    {
      name: HABIT_TIERS.contractor_pro.name,
      price: HABIT_TIERS.contractor_pro.priceLabel,
      period: 'month',
      features: HABIT_TIERS.contractor_pro.features,
      href: '/checkout/contractor_pro',
      cta: 'Start Contractor Pro',
      recommended: true,
    },
    {
      name: IC_BUNDLE.tierName,
      price: IC_BUNDLE.priceLabel,
      period: 'one site',
      features: IC_BUNDLE.featureBullets,
      href: '/checkout/ic_project',
      cta: IC_BUNDLE.ctaBuy,
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0e27] via-[#1a1f3a] to-[#0a0e27]">
      {/* ===== HERO SECTION ===== */}
      <section className="relative overflow-hidden px-4 py-20 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center space-y-6 mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full">
              <Zap className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-medium text-indigo-300">
                Essential pre-bid diligence for data center sites
              </span>
            </div>
            
            <h1 className="text-5xl md:text-6xl font-bold text-white leading-tight">
              Reg Guard for{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
                Data Centers
              </span>
            </h1>
            
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              Data center schedules die when AHJ permits, utility interconnection, and
              FAST-41 / large-load diligence run as separate surprises. Reg Guard is the
              pre-bid Bid Risk Receipt: contingency band, local gotchas, and Source or
              Unverified lines you can forward before the bid goes out — strongest citeable
              coverage today in Dallas / Plano / Austin.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
              <button
                onClick={() => {
                  const element = document.getElementById('free-trial-form');
                  if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  } else {
                    window.location.href = '/data-center#free-trial-form';
                  }
                }}
                className="px-8 py-3 bg-indigo-500 hover:bg-indigo-600 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
              >
                Run free DC site lookup <ArrowRight className="w-4 h-4" />
              </button>
              <a
                href="/checkout/ic_project"
                className="px-8 py-3 border border-indigo-500/30 hover:border-indigo-500 text-indigo-300 font-semibold rounded-lg transition text-center"
              >
                {IC_BUNDLE.ctaBuy}
              </a>
            </div>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-3 gap-4 max-w-2xl mx-auto">
            <div className="text-center">
              <div className="text-2xl font-bold text-indigo-400">AHJ + utility</div>
              <div className="text-sm text-gray-400">Parallel-track risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">Bid Risk Receipt</div>
              <div className="text-sm text-gray-400">Forward before bid day</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-400">DFW / Austin</div>
              <div className="text-sm text-gray-400">Citeable beachhead</div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== PRIMARY CAPABILITIES (Data Center) ===== */}
      <section className="px-4 py-16 sm:px-6 lg:px-8 bg-indigo-500/5 border-y border-indigo-500/10">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Why Reg Guard is essential on data center bids
            </h2>
            <p className="text-gray-300 max-w-2xl mx-auto">
              Large-load schedules fail when city permits, utility interconnection, and
              federal large-load diligence are treated as one queue. Surface the parallel
              tracks before bid day — with Source or Unverified honesty.
            </p>
            <p className="mt-4">
              <a
                href="/moratorium-radar"
                className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-300 hover:text-cyan-200"
              >
                Open moratorium radar <ArrowRight className="w-4 h-4" />
              </a>
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {dataCenterCapabilities.map((cap, idx) => (
              <div
                key={idx}
                className="group relative bg-gradient-to-br from-indigo-900/20 to-purple-900/20 border border-indigo-500/20 hover:border-indigo-400/40 rounded-xl p-6 transition-all hover:shadow-xl hover:shadow-indigo-500/10"
              >
                {/* Status Badge */}
                <div className={`absolute top-4 right-4 px-2 py-1 rounded text-xs font-semibold ${
                  cap.status === 'ready' ? 'bg-green-500/20 text-green-300' :
                  cap.status === 'beta' ? 'bg-yellow-500/20 text-yellow-300' :
                  'bg-gray-500/20 text-gray-300'
                }`}>
                  {cap.status === 'ready' ? '✓ Ready' : cap.status === 'beta' ? '⚡ Beta' : '📅 Coming'}
                </div>

                {/* Icon */}
                <div className="w-12 h-12 bg-indigo-500/20 rounded-lg flex items-center justify-center mb-4 text-indigo-300 group-hover:text-indigo-200 transition">
                  {cap.icon}
                </div>

                {/* Content */}
                <h3 className="text-lg font-semibold text-white mb-2">{cap.title}</h3>
                <p className="text-gray-400 text-sm mb-4">{cap.description}</p>

                {/* Value Proposition */}
                <div className="flex items-center justify-between pt-4 border-t border-indigo-500/10">
                  <span className="text-xs text-gray-500">Available in</span>
                  <span className="text-indigo-300 font-semibold text-sm">{cap.value}</span>
                </div>
              </div>
            ))}
          </div>

          {/* CTA */}
          <div className="mt-12 text-center">
            <a
              href="/checkout/contractor_pro"
              className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white font-semibold rounded-lg transition inline-flex items-center justify-center gap-2 mx-auto"
            >
              Contractor Pro bid desk — $149/mo <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      {/* ===== SECONDARY CAPABILITIES ===== */}
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h3 className="text-2xl font-bold text-white mb-8">Other Powerful Capabilities</h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {otherCapabilities.map((cap, idx) => (
              <div key={idx} className="bg-indigo-900/20 border border-indigo-500/10 rounded-lg p-4 hover:bg-indigo-900/30 transition">
                <div className="flex items-start gap-3">
                  <div className="text-indigo-400 mt-1">{cap.icon}</div>
                  <div>
                    <h4 className="font-semibold text-white text-sm">{cap.title}</h4>
                    <p className="text-gray-400 text-xs">{cap.desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== PRICING — Stripe checkout, same ladder as the rest of the app ===== */}
      <section className="px-4 py-16 sm:px-6 lg:px-8 bg-indigo-500/5 border-t border-indigo-500/10">
        <div className="max-w-6xl mx-auto">
          <h3 className="text-3xl font-bold text-white text-center mb-4">
            Plans for Every Stage
          </h3>
          <p className="text-center text-gray-300 max-w-2xl mx-auto mb-10">
            Large-load sites need more than a punch list preview. The{' '}
            <span className="text-emerald-200 font-semibold">{IC_BUNDLE.productName}</span> is the
            counsel-ready ZIP for one address — memo, DOCX, CSVs, parallel clocks.
          </p>
          <IcDiligenceBundlePitch className="mb-12 max-w-3xl mx-auto" />

          <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-6 max-w-6xl mx-auto">
            {pricingPlans.map((plan, idx) => (
              <div
                key={idx}
                className={`rounded-xl border p-8 transition ${
                  plan.recommended
                    ? 'bg-gradient-to-br from-indigo-900/40 to-purple-900/40 border-indigo-400 shadow-xl shadow-indigo-500/20'
                    : 'bg-indigo-900/20 border-indigo-500/20 hover:border-indigo-500/40'
                }`}
              >
                {plan.recommended && (
                  <div className="mb-4 inline-block px-3 py-1 bg-gradient-to-r from-indigo-500 to-purple-500 text-white text-xs font-bold rounded-full">
                    RECOMMENDED
                  </div>
                )}
                <h4 className="text-2xl font-bold text-white mb-2">{plan.name}</h4>
                <div className="mb-6">
                  <span className="text-4xl font-bold text-indigo-300">{plan.price}</span>
                  <span className="text-gray-400 ml-2">/{plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, fidx) => (
                    <li key={fidx} className="text-gray-300 text-sm flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <a
                  href={plan.href}
                  className={`block w-full py-3 rounded-lg font-semibold transition text-center ${
                    plan.recommended
                      ? 'bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white'
                      : 'bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300'
                  }`}
                >
                  {plan.cta}
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== TRUST SECTION ===== */}
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-8 text-center">
          <div>
            <Lock className="w-8 h-8 text-indigo-400 mx-auto mb-4" />
            <h4 className="font-semibold text-white mb-2">Card handling</h4>
            <p className="text-gray-400 text-sm">Paid upgrades go through Stripe. Reg Guard does not store cards.</p>
          </div>
          <div>
            <Shield className="w-8 h-8 text-indigo-400 mx-auto mb-4" />
            <h4 className="font-semibold text-white mb-2">Planning aid</h4>
            <p className="text-gray-400 text-sm">Not a quote, sealed bid, or interconnection study. Confirm every line with the AHJ.</p>
          </div>
          <div>
            <Users className="w-8 h-8 text-indigo-400 mx-auto mb-4" />
            <h4 className="font-semibold text-white mb-2">Support</h4>
            <p className="text-gray-400 text-sm">Email support@regguardagent.com — we do not staff 24/7 compliance experts.</p>
          </div>
        </div>
      </section>

    </div>
  );
}
