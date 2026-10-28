/**
 * RegGuard Signup & Payment Page
 * Stripe integration for free trial signup
 */

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadStripe, Stripe } from '@stripe/stripe-js';
import { ArrowLeft, CheckCircle } from 'lucide-react';

interface FormData {
  email: string;
  company_name: string;
  first_name: string;
  last_name: string;
}

export default function SignupPage() {
  const navigate = useNavigate();
  const stripeRef = useRef<Stripe | null>(null);
  
  const [formData, setFormData] = useState<FormData>({
    email: '',
    company_name: '',
    first_name: '',
    last_name: '',
  });
  const [loading, setLoading] = useState(false);
  const [error] = useState('');
  const [success] = useState(false);

  // Initialize Stripe
  useEffect(() => {
    const initStripe = async () => {
      const stripe = await loadStripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY || 'pk_test_placeholder');
      stripeRef.current = stripe;
    };
    initStripe();
    window.scrollTo(0, 0);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(false);
    navigate('/pricing');
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="mb-6 flex justify-center">
            <CheckCircle className="w-16 h-16 text-green-400" />
          </div>
          <h1 className="text-4xl font-black text-white mb-4">Welcome to RegGuard!</h1>
          <p className="text-gray-300 mb-8">
            Your free 14-day trial has been activated. Redirecting to dashboard...
          </p>
          <div className="flex justify-center">
            <div className="w-8 h-8 border-4 border-purple-500 border-t-blue-500 rounded-full animate-spin"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-4 py-16">
      <div className="max-w-md mx-auto">
        {/* Back Button */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-purple-400 hover:text-purple-300 mb-8 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </button>

        {/* Card */}
        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-purple-500/20 rounded-3xl p-8">
          <h1 className="text-3xl font-black text-white mb-2">Start Free Trial</h1>
          <p className="text-gray-400 mb-8">14 days free. Card required but won't be charged until trial ends.</p>

          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* First Name */}
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">First Name</label>
              <input
                type="text"
                name="first_name"
                value={formData.first_name}
                onChange={handleInputChange}
                placeholder="John"
                className="w-full px-4 py-2 bg-slate-900/50 border border-purple-500/20 rounded-lg text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none transition"
              />
            </div>

            {/* Last Name */}
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">Last Name</label>
              <input
                type="text"
                name="last_name"
                value={formData.last_name}
                onChange={handleInputChange}
                placeholder="Doe"
                className="w-full px-4 py-2 bg-slate-900/50 border border-purple-500/20 rounded-lg text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none transition"
              />
            </div>

            {/* Company Name */}
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">Company Name</label>
              <input
                type="text"
                name="company_name"
                value={formData.company_name}
                onChange={handleInputChange}
                placeholder="Acme Solar"
                className="w-full px-4 py-2 bg-slate-900/50 border border-purple-500/20 rounded-lg text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none transition"
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="you@company.com"
                className="w-full px-4 py-2 bg-slate-900/50 border border-purple-500/20 rounded-lg text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none transition"
              />
            </div>

            <p className="text-sm text-gray-400">
              Reg Guard does not create a password account. Buy a plan and use that email on My Orders.
            </p>

            {/* Terms */}
            <p className="text-xs text-gray-400 text-center">
              By signing up, you agree to our Terms of Service and Privacy Policy.
            </p>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Processing...' : 'Start Free Trial'}
            </button>
          </form>

          {/* Trial Info */}
          <div className="mt-6 pt-6 border-t border-purple-500/10">
            <div className="space-y-2 text-sm text-gray-400">
              <p>✓ 14 days free access</p>
              <p>✓ Full feature access</p>
              <p>✓ Cancel anytime</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
