/**
 * User onboarding and signup flow with Stripe payment gate.
 * Captures Email, Password, and Contractor Company Name before checkout.
 */

import { useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { toast } from 'react-toastify';
import { backendUrl } from './env';
import './signup-form.css';

interface SignupFormProps {
  onSuccess?: () => void;
}

export function SignupForm({ onSuccess }: SignupFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateForm = (): boolean => {
    setError(null);

    if (!email.trim()) {
      setError('Email is required');
      return false;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Invalid email address');
      return false;
    }

    if (!password.trim()) {
      setError('Password is required');
      return false;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return false;
    }

    if (!companyName.trim()) {
      setError('Company name is required');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Call backend to create Stripe Checkout Session
      const response = await fetch(backendUrl('/auth/create-checkout-session'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim(),
          password: password.trim(),
          company_name: companyName.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Checkout session creation failed (HTTP ${response.status})`);
      }

      const data = (await response.json()) as { checkout_url?: string };
      const checkoutUrl = data.checkout_url;

      if (!checkoutUrl) {
        throw new Error('No checkout URL returned from server');
      }

      // Redirect to Stripe Checkout
      window.location.href = checkoutUrl;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Signup failed. Please try again.';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rg-signup-container">
      <div className="rg-signup-card">
        <h1 className="rg-signup-title">Welcome to RegGuard</h1>
        <p className="rg-signup-subtitle">
          Agentic compliance assistant for contractors. Start your 14-day free trial.
        </p>

        <form onSubmit={handleSubmit} className="rg-signup-form">
          {error && (
            <div className="rg-signup-error">
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          )}

          <div className="rg-form-group">
            <label htmlFor="email" className="rg-form-label">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              className="rg-form-input"
              required
            />
          </div>

          <div className="rg-form-group">
            <label htmlFor="password" className="rg-form-label">
              Password
            </label>
            <input
              id="password"
              type="password"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              className="rg-form-input"
              required
            />
          </div>

          <div className="rg-form-group">
            <label htmlFor="company_name" className="rg-form-label">
              Contractor Company Name
            </label>
            <input
              id="company_name"
              type="text"
              placeholder="e.g., Bondale Contractors Inc"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              disabled={loading}
              className="rg-form-input"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="rg-signup-submit"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="rg-spinner" />
                Creating checkout...
              </>
            ) : (
              'Continue to Payment'
            )}
          </button>

          <p className="rg-signup-terms">
            By continuing, you agree to our Terms of Service and Privacy Policy. SMS is not required —
            texting is an optional separate step later. Your first 14 days are free.
          </p>
        </form>
      </div>
    </div>
  );
}
