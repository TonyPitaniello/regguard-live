/**
 * PremiumCheckoutPage.tsx
 * Multi-segment checkout: contractor_pro, ic_project, ic_annual, sponsor
 */

import { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { backendUrl } from '../env';

const stripePromise = loadStripe(
  import.meta.env.VITE_STRIPE_PUBLIC_KEY || 'pk_test_placeholder'
);

const TIERS = {
  contractor_pro: {
    name: 'Contractor Pro',
    segment: 'Contractor',
    price: '$149/month',
    price_cents: 14900,
    mode: 'subscription' as const,
    description: 'Unlimited lookups and punch lists for active contractors',
    features: [
      'Unlimited free lookups',
      'Full punch lists & timelines',
      'Saved project history',
      'Priority email support',
    ],
    delivery_time: 'Instant access',
    color: 'from-emerald-600 to-green-600',
  },
  ic_project: {
    name: 'IC Project Report',
    segment: 'IC Consultant',
    price: '$1,500',
    price_cents: 150000,
    mode: 'payment' as const,
    description: 'One-time full project report package',
    features: [
      'Research memo (PDF)',
      'Contractor punch list (PDF)',
      'Permit application package',
      'Same-day delivery',
    ],
    delivery_time: 'Within 24 hours',
    color: 'from-blue-600 to-indigo-600',
  },
  ic_annual: {
    name: 'IC Annual',
    segment: 'IC Consultant',
    price: '$15,000/year',
    price_cents: 1500000,
    mode: 'subscription' as const,
    description: 'Annual subscription for unlimited IC project reports',
    features: [
      'Unlimited project reports',
      'Priority same-day turnaround',
      'Portfolio monitoring alerts',
      'Dedicated account support',
    ],
    delivery_time: 'Instant access',
    color: 'from-indigo-600 to-blue-600',
  },
  sponsor: {
    name: 'Sponsor',
    segment: 'Sponsor',
    price: '$1,500/month',
    price_cents: 150000,
    mode: 'subscription' as const,
    description: 'Monthly sponsorship for utilities and partners',
    features: [
      'Sponsored placement & co-branding',
      'Lead sharing options',
      'Monthly reporting',
      'Partner success manager',
    ],
    delivery_time: 'Onboarding within 48 hours',
    color: 'from-amber-600 to-orange-600',
  },
};

type TierKey = keyof typeof TIERS;

function resolveTierKey(raw?: string | null): TierKey {
  if (raw && raw in TIERS) return raw as TierKey;
  // Legacy aliases
  if (raw === 'premium' || raw === 'enterprise') return 'ic_project';
  return 'ic_project';
}

export default function PremiumCheckoutPage() {
  const navigate = useNavigate();
  const { tier: tierParam } = useParams();
  const [searchParams] = useSearchParams();
  const initialTier = resolveTierKey(tierParam || searchParams.get('tier'));

  const [step, setStep] = useState<'selection' | 'checkout' | 'success' | 'error'>(
    tierParam || searchParams.get('tier') ? 'checkout' : 'selection'
  );
  const [selectedTier, setSelectedTier] = useState<TierKey>(initialTier);
  const [error, setError] = useState('');

  useEffect(() => {
    const key = resolveTierKey(tierParam || searchParams.get('tier'));
    setSelectedTier(key);
    if (tierParam || searchParams.get('tier')) {
      setStep('checkout');
    }
  }, [tierParam, searchParams]);

  const handleTierSelect = (tierKey: string) => {
    setSelectedTier(resolveTierKey(tierKey));
    setStep('checkout');
  };

  const handleBack = () => {
    if (step === 'checkout') {
      setStep('selection');
      setError('');
    } else if (step === 'success' || step === 'error') {
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <h1 className="text-white font-black text-xl">RegGuard Checkout</h1>
          {step !== 'selection' && (
            <button onClick={handleBack} className="text-gray-400 hover:text-white transition">
              ← Back
            </button>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {step === 'selection' && <TierSelectionStep onSelect={handleTierSelect} />}
        {step === 'checkout' && (
          <CheckoutFormStep
            tier={selectedTier}
            onBack={handleBack}
            onSuccess={() => setStep('success')}
            onError={(err) => {
              setError(err);
              setStep('error');
            }}
          />
        )}
        {step === 'success' && <SuccessStep tier={selectedTier} />}
        {step === 'error' && <ErrorStep error={error} onRetry={() => setStep('checkout')} />}
      </main>
    </div>
  );
}

function TierSelectionStep({ onSelect }: { onSelect: (tier: string) => void }) {
  return (
    <div>
      <h2 className="text-3xl font-black text-white mb-2">Choose Your Plan</h2>
      <p className="text-gray-400 mb-12">Select the tier that fits your segment</p>

      <div className="grid md:grid-cols-2 gap-6">
        {Object.entries(TIERS).map(([key, tier]) => (
          <div
            key={key}
            className={`bg-gradient-to-br ${tier.color} rounded-lg p-1 hover:scale-[1.02] transition transform`}
          >
            <div className="bg-slate-900 rounded-lg p-7 h-full">
              <p className="text-xs uppercase tracking-wider text-purple-300 font-bold mb-1">
                {tier.segment}
              </p>
              <h3 className="text-2xl font-bold text-white mb-2">{tier.name}</h3>
              <p className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400 mb-4">
                {tier.price}
              </p>
              <p className="text-gray-400 mb-6 text-sm">{tier.description}</p>
              <ul className="space-y-2 mb-8">
                {tier.features.map((feature) => (
                  <li key={feature} className="text-gray-300 flex items-start text-sm">
                    <span className="mr-3 text-green-400">✓</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <p className="text-sm text-gray-500 mb-4">📦 {tier.delivery_time}</p>
              <button
                onClick={() => onSelect(key)}
                className={`w-full px-6 py-3 bg-gradient-to-r ${tier.color} text-white font-bold rounded-lg hover:shadow-lg transition`}
              >
                Select {tier.name}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CheckoutFormStep({
  tier,
  onBack,
  onSuccess,
  onError,
}: {
  tier: TierKey;
  onBack: () => void;
  onSuccess: () => void;
  onError: (error: string) => void;
}) {
  const tierInfo = TIERS[tier];

  return (
    <div>
      <h2 className="text-3xl font-black text-white mb-2">Complete Your Order</h2>
      <p className="text-gray-400 mb-12">
        {tierInfo.name} — {tierInfo.price}
        {tierInfo.mode === 'subscription' ? ' (subscription)' : ' (one-time)'}
      </p>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <div className="bg-slate-800 border border-purple-500/20 rounded-lg p-6 sticky top-24">
            <h3 className="text-lg font-bold text-white mb-6">Order Summary</h3>
            <div className="space-y-4 mb-6">
              <div className="flex justify-between">
                <span className="text-gray-400">{tierInfo.name}</span>
                <span className="text-white font-bold">{tierInfo.price}</span>
              </div>
              <div className="border-t border-gray-700 pt-4 flex justify-between">
                <span className="text-white font-bold">Total</span>
                <span className="text-2xl font-black text-purple-400">{tierInfo.price}</span>
              </div>
            </div>
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4 text-sm text-purple-200">
              <p>✓ {tierInfo.mode === 'payment' ? 'One-time payment' : 'Recurring billing'}</p>
              <p>✓ {tierInfo.delivery_time}</p>
            </div>
            <button onClick={onBack} className="mt-4 text-sm text-gray-400 hover:text-white">
              Change plan
            </button>
          </div>
        </div>

        <div className="lg:col-span-2">
          <Elements stripe={stripePromise}>
            <PaymentForm
              tier={tier}
              tierPrice={tierInfo.price}
              onSuccess={onSuccess}
              onError={onError}
            />
          </Elements>
        </div>
      </div>
    </div>
  );
}

function PaymentForm({
  tier,
  tierPrice,
  onSuccess,
  onError,
}: {
  tier: string;
  tierPrice: string;
  onSuccess: () => void;
  onError: (error: string) => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [cardError, setCardError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setCardError('');

    if (!stripe || !elements) {
      onError('Stripe not loaded');
      setLoading(false);
      return;
    }

    try {
      const trialId = sessionStorage.getItem('trialId') || 'unknown';
      const userId = sessionStorage.getItem('userId') || email || 'anonymous';

      // Persist email so /checkout/success can load orders after Stripe redirect
      sessionStorage.setItem('userEmail', email.trim().toLowerCase());
      if (name.trim()) sessionStorage.setItem('userName', name.trim());

      const response = await fetch(backendUrl('/checkout'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trial_id: trialId,
          user_id: userId,
          tier,
          email: email.trim().toLowerCase(),
          name: name.trim(),
          success_url: `${window.location.origin}/checkout/success`,
          cancel_url: `${window.location.origin}/checkout/${tier}`,
        }),
      });

      if (!response.ok) throw new Error('Checkout creation failed');

      const { checkout_url } = await response.json();
      if (checkout_url) {
        window.location.href = checkout_url;
      } else {
        onSuccess();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Payment failed';
      setCardError(message);
      onError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="email" className="block text-white font-bold mb-2">
          Email Address *
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
          required
          className="w-full px-4 py-3 bg-slate-800 border border-purple-500/30 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
        />
      </div>

      <div>
        <label htmlFor="name" className="block text-white font-bold mb-2">
          Full Name *
        </label>
        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="John Doe"
          required
          className="w-full px-4 py-3 bg-slate-800 border border-purple-500/30 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
        />
      </div>

      <div>
        <label className="block text-white font-bold mb-2">Payment Details *</label>
        <div className="p-4 bg-slate-800 border border-purple-500/30 rounded-lg">
          <CardElement
            options={{
              style: {
                base: {
                  fontSize: '16px',
                  color: '#fff',
                  '::placeholder': { color: '#9CA3AF' },
                },
                invalid: { color: '#EF4444' },
              },
            }}
          />
        </div>
      </div>

      {cardError && (
        <div className="flex gap-3 p-4 bg-red-500/20 border border-red-500/30 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-red-200 text-sm">{cardError}</p>
        </div>
      )}

      <div className="bg-slate-800/50 border border-purple-500/10 rounded-lg p-4 text-sm text-gray-400">
        By clicking &quot;Complete Purchase&quot;, you agree to our Terms of Service. Payment is
        processed securely through Stripe.
      </div>

      <button
        type="submit"
        disabled={loading || !stripe || !elements}
        className="w-full px-6 py-4 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold text-lg rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading && <Loader className="w-5 h-5 animate-spin" />}
        {loading ? 'Processing...' : `Complete Purchase — ${tierPrice}`}
      </button>
    </form>
  );
}

function SuccessStep({ tier }: { tier: TierKey }) {
  const tierInfo = TIERS[tier];
  const navigate = useNavigate();

  return (
    <div className="text-center">
      <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-6" />
      <h2 className="text-3xl font-black text-white mb-4">Payment Successful!</h2>
      <p className="text-gray-300 mb-8 max-w-2xl mx-auto">
        Thank you! Your {tierInfo.name} purchase has been processed.
      </p>
      <button
        onClick={() => navigate('/orders')}
        className="px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-lg hover:shadow-lg transition"
      >
        View My Orders
      </button>
    </div>
  );
}

function ErrorStep({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="text-center">
      <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-6" />
      <h2 className="text-3xl font-black text-white mb-4">Payment Failed</h2>
      <p className="text-gray-300 mb-8 max-w-2xl mx-auto">{error}</p>
      <button
        onClick={onRetry}
        className="px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-lg hover:shadow-lg transition"
      >
        Try Again
      </button>
    </div>
  );
}
