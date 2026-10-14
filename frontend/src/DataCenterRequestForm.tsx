import { useState } from 'react';
import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { toast } from 'react-toastify';
import { backendUrl } from './env';
import './data-center-request-form.css';

interface DataCenterRequestFormProps {
  onSuccess?: (analysis: any) => void;
}

export function DataCenterRequestForm({ onSuccess }: DataCenterRequestFormProps) {
  const [formData, setFormData] = useState({
    address: '',
    city: '',
    state: 'TX',
    projected_mw: 100,
    requester_name: '',
    requester_email: '',
    requester_phone: '',
    company_name: '',
    role: 'Data Center Developer',
    expected_timeline_months: 12,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  const validateForm = (): boolean => {
    setError(null);

    if (!formData.address.trim()) {
      setError('Project address is required');
      return false;
    }
    if (!formData.city.trim()) {
      setError('City is required');
      return false;
    }
    if (!formData.projected_mw || formData.projected_mw < 1) {
      setError('Projected MW must be at least 1');
      return false;
    }
    if (!formData.requester_name.trim()) {
      setError('Your name is required');
      return false;
    }
    if (!formData.requester_email.trim()) {
      setError('Email is required');
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.requester_email)) {
      setError('Invalid email address');
      return false;
    }
    if (!formData.company_name.trim()) {
      setError('Company name is required');
      return false;
    }

    return true;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'projected_mw' || name === 'expected_timeline_months' ? parseInt(value) : value,
    }));
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
      const response = await fetch(backendUrl('/api/data-center-analysis/request'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Analysis request failed (HTTP ${response.status})`);
      }

      const data = await response.json();
      setSuccess(true);
      setAnalysisResult(data.analysis);
      toast.success('Request saved. This is not a site lookup.');
      
      if (onSuccess) {
        onSuccess(data.analysis);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analysis request failed. Please try again.';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  if (success && analysisResult) {
    return (
      <div className="dc-request-container">
        <div className="dc-success-card">
          <CheckCircle2 size={48} className="dc-success-icon" />
          <h2 className="dc-success-title">Request saved</h2>
          <p className="dc-success-message">
            This form does not run a site lookup and does not schedule a call.
            Use the free lookup above for a Bid Risk Receipt, or buy the IC Diligence Bundle for the counsel ZIP.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="dc-request-container">
      <div className="dc-request-card">
        <h1 className="dc-request-title">Talk about a large-load site</h1>
        <p className="dc-request-subtitle">
          A conversation request only. It does not score the site, email a report, or schedule a call.
        </p>

        <form onSubmit={handleSubmit} className="dc-request-form">
          {error && (
            <div className="dc-error">
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          )}

          <div className="dc-form-section">
            <h3>Project Details</h3>

            <div className="dc-form-group">
              <label htmlFor="address">Project Address *</label>
              <input
                id="address"
                name="address"
                type="text"
                placeholder="123 Tech Drive"
                value={formData.address}
                onChange={handleChange}
                disabled={loading}
                required
              />
            </div>

            <div className="dc-form-row">
              <div className="dc-form-group">
                <label htmlFor="city">City *</label>
                <input
                  id="city"
                  name="city"
                  type="text"
                  placeholder="Austin"
                  value={formData.city}
                  onChange={handleChange}
                  disabled={loading}
                  required
                />
              </div>

              <div className="dc-form-group">
                <label htmlFor="state">State *</label>
                <select
                  id="state"
                  name="state"
                  value={formData.state}
                  onChange={handleChange}
                  disabled={loading}
                  required
                >
                  <option value="TX">Texas</option>
                  <option value="CA">California</option>
                  <option value="VA">Virginia</option>
                  <option value="NC">North Carolina</option>
                  <option value="NY">New York</option>
                  <option value="IL">Illinois</option>
                  <option value="AZ">Arizona</option>
                  <option value="OR">Oregon</option>
                  <option value="WA">Washington</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div className="dc-form-group">
                <label htmlFor="projected_mw">Projected MW *</label>
                <input
                  id="projected_mw"
                  name="projected_mw"
                  type="number"
                  min="1"
                  max="1000"
                  value={formData.projected_mw}
                  onChange={handleChange}
                  disabled={loading}
                  required
                />
              </div>
            </div>

            <div className="dc-form-group">
              <label htmlFor="expected_timeline_months">Expected Timeline (months)</label>
              <input
                id="expected_timeline_months"
                name="expected_timeline_months"
                type="number"
                min="1"
                max="60"
                value={formData.expected_timeline_months}
                onChange={handleChange}
                disabled={loading}
              />
            </div>
          </div>

          <div className="dc-form-section">
            <h3>Your Information</h3>

            <div className="dc-form-group">
              <label htmlFor="requester_name">Your Name *</label>
              <input
                id="requester_name"
                name="requester_name"
                type="text"
                placeholder="John Smith"
                value={formData.requester_name}
                onChange={handleChange}
                disabled={loading}
                required
              />
            </div>

            <div className="dc-form-row">
              <div className="dc-form-group">
                <label htmlFor="requester_email">Email *</label>
                <input
                  id="requester_email"
                  name="requester_email"
                  type="email"
                  placeholder="john@company.com"
                  value={formData.requester_email}
                  onChange={handleChange}
                  disabled={loading}
                  required
                />
              </div>

              <div className="dc-form-group">
                <label htmlFor="requester_phone">Phone</label>
                <input
                  id="requester_phone"
                  name="requester_phone"
                  type="tel"
                  placeholder="+1 (555) 000-0000"
                  value={formData.requester_phone}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="dc-form-group">
              <label htmlFor="company_name">Company/Developer Name *</label>
              <input
                id="company_name"
                name="company_name"
                type="text"
                placeholder="Acme Data Centers Inc"
                value={formData.company_name}
                onChange={handleChange}
                disabled={loading}
                required
              />
            </div>

            <div className="dc-form-group">
              <label htmlFor="role">Your Role</label>
              <select
                id="role"
                name="role"
                value={formData.role}
                onChange={handleChange}
                disabled={loading}
              >
                <option value="Data Center Developer">Data Center Developer</option>
                <option value="Construction Firm">Construction Firm</option>
                <option value="Permitting Consultant">Permitting Consultant</option>
                <option value="Real Estate Advisor">Real Estate Advisor</option>
                <option value="Infrastructure Investor">Infrastructure Investor</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          <button type="submit" disabled={loading} className="dc-submit-btn">
            {loading ? (
              <>
                <Loader2 size={18} className="spinner" />
                Analyzing...
              </>
            ) : (
              'Send conversation request'
            )}
          </button>

          <p className="dc-form-note">
            The free lookup above is the product. This form only saves a note for the team.
          </p>
        </form>
      </div>
    </div>
  );
}
