/**
 * Unused leftover. Signup does not create a password account.
 * /signup redirects to pricing.
 */

import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import './signup-form.css';

export function SignupForm() {
  const [error, setError] = useState<string | null>(
    'Reg Guard does not create a password account. Buy a plan from pricing and use that email on My Orders.'
  );

  return (
    <div className="rg-signup-container">
      <div className="rg-signup-card">
        <h1 className="rg-signup-title">My Orders</h1>
        <p className="rg-signup-subtitle">
          Use the email on your purchase. There is no password to set or reset.
        </p>
        {error && (
          <div className="rg-signup-error">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}
        <a href="/pricing" className="rg-signup-submit" onClick={() => setError(null)}>
          View plans
        </a>
      </div>
    </div>
  );
}
