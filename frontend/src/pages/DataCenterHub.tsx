/**
 * RegGuard Data Center Hub - Premium UI/UX Redesign
 * Focuses on data center interconnection with clear capability hierarchy
 * Collects credit card info even for free trial (standard SaaS)
 */

import { useState } from 'react';
import {
  Zap,
  MapPin,
  Clock,
  DollarSign,
  CheckCircle,
  AlertTriangle,
  FileText,
  Users,
  TrendingUp,
  Shield,
  Code,
  BookOpen,
  ArrowRight,
  Lock,
  Gauge,
  Workflow
} from 'lucide-react';

interface DataCenterCapability {
  icon: React.ReactNode;
  title: string;
  description: string;
  status: 'ready' | 'beta' | 'coming';
  value: string;
}

export function DataCenterHub() {
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<'free' | 'pro'>('free');

  // === PRIMARY: Data Center Capabilities ===
  const dataCenterCapabilities: DataCenterCapability[] = [
    {
      icon: <Zap className="w-6 h-6" />,
      title: 'Electrical Interconnection Analysis',
      description: 'AI-powered analysis of utility coordination, voltage drop, and compliance',
      status: 'ready',
      value: '$0'
    },
    {
      icon: <MapPin className="w-6 h-6" />,
      title: 'Site Permit Orchestration',
      description: 'Auto-generate compliant permits for 50+ jurisdictions',
      status: 'ready',
      value: '$0'
    },
    {
      icon: <Clock className="w-6 h-6" />,
      title: 'Interconnection Timeline Predictor',
      description: 'ML-powered ETA for FERC 556 & utility studies',
      status: 'ready',
      value: '$0'
    },
    {
      icon: <AlertTriangle className="w-6 h-6" />,
      title: 'Risk & Compliance Alerts',
      description: 'Real-time flagging of regulatory roadblocks',
      status: 'ready',
      value: '$0'
    },
    {
      icon: <FileText className="w-6 h-6" />,
      title: 'BIM to Compliance Parser',
      description: 'Auto-extract electrical specs from Revit files',
      status: 'beta',
      value: 'Free (Beta)'
    },
    {
      icon: <DollarSign className="w-6 h-6" />,
      title: 'Capital Readiness Modeling',
      description: 'Financial modeling for interconnection costs',
      status: 'coming',
      value: 'Q3 2026'
    }
  ];

  // === SECONDARY: Other Capabilities ===
  const otherCapabilities = [
    { icon: <Users className="w-5 h-5" />, title: 'Contractor Queue Management', desc: 'Manage 10x faster project queues' },
    { icon: <BookOpen className="w-5 h-5" />, title: 'Regulatory Research', desc: 'Federal, state, county regulations' },
    { icon: <Gauge className="w-5 h-5" />, title: 'Project Analytics', desc: '1,000+ projects tracked' },
    { icon: <Workflow className="w-5 h-5" />, title: 'Form Auto-Fill', desc: 'FERC, PJM, MISO forms pre-populated' },
  ];

  const pricingPlans = [
    {
      name: 'Contractor Free',
      price: '$0',
      period: 'lookups',
      features: [
        '✓ Free site diligence lookup',
        '✓ Environmental risk summary',
        '✓ Punch list highlights',
        '✓ Text or email results',
        'No credit card required',
      ],
    },
    {
      name: 'Contractor Pro',
      price: '$149',
      period: 'month',
      features: [
        '✓ Unlimited lookups',
        '✓ Full punch lists & timelines',
        '✓ Saved project history',
        '✓ Priority email support',
      ],
      recommended: true,
    },
    {
      name: 'IC Project Report',
      price: '$1,500',
      period: 'one-time',
      features: [
        '✓ Full research memo (PDF)',
        '✓ Punch list + permit package',
        '✓ Same-day delivery',
        '✓ Accuracy guarantee',
      ],
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
                IC Project — $1,500
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
            <button
              onClick={() => { setSelectedPlan('pro'); setShowPaymentModal(true); }}
              className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2 mx-auto"
            >
              Unlock Full Data Center Suite <ArrowRight className="w-4 h-4" />
            </button>
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

      {/* ===== PRICING WITH CREDIT CARD COLLECTION ===== */}
      <section className="px-4 py-16 sm:px-6 lg:px-8 bg-indigo-500/5 border-t border-indigo-500/10">
        <div className="max-w-6xl mx-auto">
          <h3 className="text-3xl font-bold text-white text-center mb-12">
            Plans for Every Stage
          </h3>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
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
                <button
                  onClick={() => {
                    if (idx === 0) {
                      setSelectedPlan('free');
                      setShowPaymentModal(true);
                    } else if (idx === 1) {
                      window.location.href = '/checkout/contractor_pro';
                    } else {
                      window.location.href = '/checkout/ic_project';
                    }
                  }}
                  className={`w-full py-3 rounded-lg font-semibold transition ${
                    plan.recommended
                      ? 'bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white'
                      : 'bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300'
                  }`}
                >
                  Get Started
                </button>
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
            <h4 className="font-semibold text-white mb-2">Enterprise Security</h4>
            <p className="text-gray-400 text-sm">SOC 2 Type II certified. Bank-grade encryption.</p>
          </div>
          <div>
            <Shield className="w-8 h-8 text-indigo-400 mx-auto mb-4" />
            <h4 className="font-semibold text-white mb-2">Compliance Guaranteed</h4>
            <p className="text-gray-400 text-sm">90%+ pass rate on all jurisdiction audits.</p>
          </div>
          <div>
            <Users className="w-8 h-8 text-indigo-400 mx-auto mb-4" />
            <h4 className="font-semibold text-white mb-2">24/7 Support</h4>
            <p className="text-gray-400 text-sm">Dedicated compliance experts on your team.</p>
          </div>
        </div>
      </section>

      {/* ===== PAYMENT MODAL ===== */}
      {showPaymentModal && (
        <PaymentModal
          plan={selectedPlan}
          onClose={() => setShowPaymentModal(false)}
          pricingPlans={pricingPlans}
        />
      )}
    </div>
  );
}

interface PaymentModalProps {
  plan: 'free' | 'pro';
  onClose: () => void;
  pricingPlans: typeof pricingPlans;
}

function PaymentModal({ plan, onClose, pricingPlans }: PaymentModalProps) {
  const [step, setStep] = useState<'info' | 'payment'>('info');
  const [formData, setFormData] = useState({
    email: '',
    company: '',
    phone: '',
    cardName: '',
    cardNumber: '',
    expiry: '',
    cvc: ''
  });

  const planDetails = plan === 'free' ? pricingPlans[0] : pricingPlans[1];

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-[#0a0e27] to-[#1a1f3a] border border-indigo-500/20 rounded-2xl max-w-md w-full shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border-b border-indigo-500/20 px-6 py-6 flex justify-between items-center">
          <h2 className="text-xl font-bold text-white">
            {step === 'info' ? 'Account Setup' : 'Payment Method'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Plan Summary */}
          <div className="bg-indigo-900/30 rounded-lg p-4 border border-indigo-500/20">
            <div className="flex justify-between items-center">
              <span className="text-gray-300">{planDetails.name}</span>
              <span className="text-indigo-300 font-bold">{planDetails.price}</span>
            </div>
          </div>

          {step === 'info' && (
            <>
              <div className="space-y-4">
                <input
                  type="email"
                  placeholder="Email"
                  className="w-full bg-indigo-900/30 border border-indigo-500/20 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                />
                <input
                  type="text"
                  placeholder="Company Name"
                  className="w-full bg-indigo-900/30 border border-indigo-500/20 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                  value={formData.company}
                  onChange={(e) => setFormData({...formData, company: e.target.value})}
                />
                <input
                  type="tel"
                  placeholder="Phone Number"
                  className="w-full bg-indigo-900/30 border border-indigo-500/20 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                  value={formData.phone}
                  onChange={(e) => setFormData({...formData, phone: e.target.value})}
                />
              </div>

              <button
                onClick={() => setStep('payment')}
                className="w-full bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white font-semibold py-2 rounded-lg transition"
              >
                Continue to Payment
              </button>
            </>
          )}

          {step === 'payment' && (
            <>
              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Full Name on Card"
                  className="w-full bg-indigo-900/30 border border-indigo-500/20 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                  value={formData.cardName}
                  onChange={(e) => setFormData({...formData, cardName: e.target.value})}
                />
                <input
                  type="text"
                  placeholder="Card Number"
                  className="w-full bg-indigo-900/30 border border-indigo-500/20 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                  value={formData.cardNumber}
                  onChange={(e) => setFormData({...formData, cardNumber: e.target.value})}
                />
                <div className="grid grid-cols-2 gap-4">
                  <input
                    type="text"
                    placeholder="MM/YY"
                    className="bg-indigo-900/30 border border-indigo-500/20 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                    value={formData.expiry}
                    onChange={(e) => setFormData({...formData, expiry: e.target.value})}
                  />
                  <input
                    type="text"
                    placeholder="CVC"
                    className="bg-indigo-900/30 border border-indigo-500/20 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                    value={formData.cvc}
                    onChange={(e) => setFormData({...formData, cvc: e.target.value})}
                  />
                </div>
              </div>

              <div className="text-xs text-gray-400 text-center">
                Your payment information is secure and encrypted
              </div>

              <button
                onClick={() => {
                  console.log('Payment submitted:', formData);
                  // TODO: Submit to backend
                  onClose();
                }}
                className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white font-semibold py-2 rounded-lg transition"
              >
                Complete Setup
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
