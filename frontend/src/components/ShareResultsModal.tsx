/**
 * ShareResultsModal.tsx
 * Modal for sharing research results via SMS or email.
 * Supports optional summary payload for free-trial results without a DB record.
 */

import React, { useState, useEffect } from 'react';
import { X, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { backendUrl } from '../env';
import type { ResultsSummaryPayload } from './SendResultsForm';

interface ShareResultsModalProps {
  isOpen: boolean;
  onClose: () => void;
  deliveryMethod: 'sms' | 'email';
  researchId?: string | null;
  summary?: ResultsSummaryPayload;
  onSuccess?: (result: { status: string; phone?: string; email?: string }) => void;
}

interface ValidationError {
  phone?: string;
  email?: string;
  general?: string;
}

export const ShareResultsModal: React.FC<ShareResultsModalProps> = ({
  isOpen,
  onClose,
  deliveryMethod,
  researchId,
  summary,
  onSuccess,
}) => {
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [smsConsent, setSmsConsent] = useState(false); // unchecked by default — SMS never required to use RegGuard
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<ValidationError>({});
  const [success, setSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [rateLimitWait, setRateLimitWait] = useState<number | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setPhone('');
      setEmail('');
      setErrors({});
      setSuccess(false);
      setSuccessMessage('');
      setRateLimitWait(null);
    }
  }, [isOpen]);

  const validatePhone = (value: string): boolean => {
    const digits = value.replace(/\D/g, '');
    return digits.length === 10 || digits.length === 11;
  };

  const validateEmail = (value: string): boolean => {
    const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return pattern.test(value);
  };

  const buildBody = (extra: Record<string, string>) => ({
    ...extra,
    ...(summary ? { summary } : {}),
    ...(researchId ? { research_id: researchId } : {}),
  });

  const handleSendSMS = async () => {
    if (!phone) {
      setErrors({ phone: 'Phone number is required only if you choose SMS — or switch to Email' });
      return;
    }
    if (!validatePhone(phone)) {
      setErrors({ phone: 'Please enter a valid US phone number (10 digits)' });
      return;
    }
    if (!smsConsent) {
      setErrors({
        phone: 'Check the optional SMS consent box, or switch to Email (SMS is never required).',
      });
      return;
    }

    setLoading(true);
    setErrors({});

    try {
      const path = researchId
        ? `/research/${researchId}/send-sms`
        : '/research/send-sms';
      const response = await fetch(backendUrl(path), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildBody({ phone_number: phone })),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 400 && data.detail?.includes('Try again in')) {
          const match = data.detail.match(/Try again in (\d+) minutes/);
          if (match) setRateLimitWait(parseInt(match[1]));
          setErrors({ general: data.detail });
        } else {
          setErrors({ general: data.detail || 'Failed to send SMS' });
        }
        return;
      }

      const displayPhone = phone.replace(/\D/g, '');
      const formattedPhone = `+1-${displayPhone.slice(-10, -7)}-${displayPhone.slice(-7, -4)}-${displayPhone.slice(-4)}`;

      setSuccess(true);
      setSuccessMessage(`Sent to ${formattedPhone}`);
      setPhone('');
      onSuccess?.({ status: 'sent', phone: data.phone });
      setTimeout(() => onClose(), 3000);
    } catch (error) {
      setErrors({ general: 'Network error. Please try again.' });
      console.error('Error sending SMS:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendEmail = async () => {
    if (!email) {
      setErrors({ email: 'Email is required' });
      return;
    }
    if (!validateEmail(email)) {
      setErrors({ email: 'Please enter a valid email address' });
      return;
    }

    setLoading(true);
    setErrors({});

    try {
      const path = researchId
        ? `/research/${researchId}/send-email`
        : '/research/send-email';
      const response = await fetch(backendUrl(path), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildBody({ email_address: email, email })),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 400 && data.detail?.includes('Try again in')) {
          const match = data.detail.match(/Try again in (\d+) minutes/);
          if (match) setRateLimitWait(parseInt(match[1]));
          setErrors({ general: data.detail });
        } else {
          setErrors({ general: data.detail || 'Failed to send email' });
        }
        return;
      }

      setSuccess(true);
      setSuccessMessage(`Sent to ${email}`);
      setEmail('');
      onSuccess?.({ status: 'sent', email: data.email });
      setTimeout(() => onClose(), 3000);
    } catch (error) {
      setErrors({ general: 'Network error. Please try again.' });
      console.error('Error sending email:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-bold text-gray-900">
            {deliveryMethod === 'sms' ? 'Send via Text' : 'Send via Email'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition" aria-label="Close">
            <X size={24} />
          </button>
        </div>

        <div className="p-6">
          {success && (
            <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg border border-green-200 mb-4">
              <CheckCircle size={20} className="text-green-600" />
              <div>
                <p className="text-sm font-medium text-green-900">{successMessage}</p>
                <p className="text-xs text-green-700 mt-1">
                  Check your {deliveryMethod === 'sms' ? 'phone' : 'inbox'}
                </p>
              </div>
            </div>
          )}

          {errors.general && (
            <div className="flex items-start gap-3 p-4 bg-red-50 rounded-lg border border-red-200 mb-4">
              <AlertCircle size={20} className="text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-900">{errors.general}</p>
                {rateLimitWait && (
                  <p className="text-xs text-red-700 mt-1">
                    Please wait {rateLimitWait} minute{rateLimitWait > 1 ? 's' : ''} before trying again
                  </p>
                )}
              </div>
            </div>
          )}

          {deliveryMethod === 'sms' && (
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
                Phone Number
              </label>
              <input
                id="phone"
                type="tel"
                placeholder="+1 (555) 123-4567 or 5551234567"
                value={phone}
                onChange={(e) => {
                  setPhone(e.target.value);
                  if (e.target.value && !validatePhone(e.target.value)) {
                    setErrors({ ...errors, phone: 'Please enter a valid US phone number (10 digits)' });
                  } else {
                    setErrors({ ...errors, phone: undefined });
                  }
                }}
                disabled={loading || success}
                className={`w-full px-4 py-2 border rounded-lg outline-none transition ${
                  errors.phone
                    ? 'border-red-300 bg-red-50 text-red-900'
                    : 'border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500'
                } disabled:bg-gray-50 disabled:text-gray-500`}
              />
              {errors.phone && (
                <p className="mt-2 text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle size={16} />
                  {errors.phone}
                </p>
              )}
              <label className="mt-3 flex items-start gap-2 text-xs text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 shrink-0"
                  checked={smsConsent}
                  onChange={(e) => setSmsConsent(e.target.checked)}
                />
                <span>
                  Optional: I agree to receive transactional SMS from RegGuard / Pitaniello Perkins LLC
                  about this research request. Message frequency varies. Message and data rates may apply.
                  Reply STOP to opt out; HELP for help. Consent is not required to use RegGuard — switch to
                  Email above to continue without texts. We do not share mobile numbers for marketing.{' '}
                  <a
                    href="https://app.regguardagent.com/privacy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 underline"
                  >
                    Privacy Policy
                  </a>
                  .
                </span>
              </label>
            </div>
          )}

          {deliveryMethod === 'email' && (
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (e.target.value && !validateEmail(e.target.value)) {
                    setErrors({ ...errors, email: 'Please enter a valid email address' });
                  } else {
                    setErrors({ ...errors, email: undefined });
                  }
                }}
                disabled={loading || success}
                className={`w-full px-4 py-2 border rounded-lg outline-none transition ${
                  errors.email
                    ? 'border-red-300 bg-red-50 text-red-900'
                    : 'border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500'
                } disabled:bg-gray-50 disabled:text-gray-500`}
              />
              {errors.email && (
                <p className="mt-2 text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle size={16} />
                  {errors.email}
                </p>
              )}
            </div>
          )}
        </div>

        <div className="flex gap-3 p-6 border-t bg-gray-50 rounded-b-lg">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            Cancel
          </button>
          <button
            onClick={deliveryMethod === 'sms' ? handleSendSMS : handleSendEmail}
            disabled={loading || success || rateLimitWait !== null}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
          >
            {loading && <Loader size={16} className="animate-spin" />}
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ShareResultsModal;
