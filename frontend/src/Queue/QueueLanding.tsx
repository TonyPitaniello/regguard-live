import React from 'react';
import { Link } from 'react-router-dom';
import './queue-landing.css';

export const QueueLanding: React.FC = () => {
  return (
    <div className="queue-landing">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <p className="queue-demo-banner" style={{
            display: 'inline-block',
            marginBottom: '1rem',
            padding: '0.4rem 0.75rem',
            border: '1px solid rgba(255,255,255,0.35)',
            borderRadius: '4px',
            fontSize: '0.85rem',
            letterSpacing: '0.02em',
          }}>
            Preview / demo tools — not a live RTO queue filing product
          </p>
          <h1>Interconnection form preview (demo)</h1>
          <p>
            Experiment with draft auto-fill helpers for common interconnection form layouts.
            This is not a live RTO filing portal — you still submit on the official RTO system.
          </p>
          <Link to="/queue/upload" className="btn-hero">
            Try demo auto-fill
          </Link>
        </div>
        <div className="hero-illustration">
          <div className="illustration">📋</div>
        </div>
      </section>

      {/* How It Works */}
      <section className="how-it-works">
        <h2>How the demo works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-number">1</div>
            <h3>Upload sample project details</h3>
            <p>Paste project details or upload a PDF with your project information</p>
          </div>
          <div className="step">
            <div className="step-number">2</div>
            <h3>Preview auto-filled fields</h3>
            <p>AI drafts field values for review — treat every field as unverified until you check it</p>
          </div>
          <div className="step">
            <div className="step-number">3</div>
            <h3>Download draft for your records</h3>
            <p>Export a draft PDF. Official filing, fees, and queue position stay on the RTO portal.</p>
          </div>
        </div>
      </section>

      {/* Supported Forms */}
      <section className="supported-forms">
        <h2>Supported Forms</h2>
        <div className="forms-grid">
          <div className="form-card">
            <div className="form-icon">📄</div>
            <h3>FERC Form 556</h3>
            <p>Large Generator Interconnection Application</p>
            <p className="capacity">&gt;20 MW</p>
          </div>
          <div className="form-card">
            <div className="form-icon">📋</div>
            <h3>FERC Form 557</h3>
            <p>Small Generator Interconnection Application</p>
            <p className="capacity">&lt;20 MW</p>
          </div>
          <div className="form-card">
            <div className="form-icon">🔌</div>
            <h3>PJM NextGen</h3>
            <p>PJM Interconnection Application</p>
            <p className="capacity">PJM Region</p>
          </div>
          <div className="form-card">
            <div className="form-icon">⚙️</div>
            <h3>MISO Interconnection</h3>
            <p>MISO Application & Queue Management</p>
            <p className="capacity">MISO Region</p>
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="benefits">
        <h2>What this demo is for</h2>
        <div className="benefits-grid">
          <div className="benefit">
            <div className="benefit-icon">⚡</div>
            <h3>Draft faster</h3>
            <p>Get a starting draft of common form fields in seconds</p>
          </div>
          <div className="benefit">
            <div className="benefit-icon">🎯</div>
            <h3>Human review required</h3>
            <p>Every field must be verified before any official filing</p>
          </div>
          <div className="benefit">
            <div className="benefit-icon">💰</div>
            <h3>Prep aid only</h3>
            <p>Does not replace IC consultants or RTO filing fees</p>
          </div>
          <div className="benefit">
            <div className="benefit-icon">📱</div>
            <h3>Easy to Use</h3>
            <p>No technical knowledge required</p>
          </div>
          <div className="benefit">
            <div className="benefit-icon">🔐</div>
            <h3>Secure</h3>
            <p>Enterprise-grade security and encryption</p>
          </div>
          <div className="benefit">
            <div className="benefit-icon">♻️</div>
            <h3>Reusable Templates</h3>
            <p>Save company info for future applications</p>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="pricing">
        <h2>Simple Pricing</h2>
        <div className="pricing-grid">
          <div className="pricing-card free">
            <h3>Free</h3>
            <div className="price">$0</div>
            <p className="period">1 form/month</p>
            <ul className="features">
              <li>✓ 1 auto-filled form</li>
              <li>✓ FERC forms only</li>
              <li>✓ PDF download</li>
              <li>✗ API access</li>
            </ul>
            <button className="btn-pricing">Get Started</button>
          </div>

          <div className="pricing-card pro">
            <h3>Pro</h3>
            <div className="price">$99<span>/mo</span></div>
            <p className="period">Most popular</p>
            <ul className="features">
              <li>✓ Unlimited forms</li>
              <li>✓ All RTOs (PJM, MISO, ERCOT)</li>
              <li>✓ PDF + batch exports</li>
              <li>✓ 100 API calls/month</li>
              <li>✓ Email support</li>
            </ul>
            <button className="btn-pricing btn-highlight">Start Pro Trial</button>
          </div>

          <div className="pricing-card enterprise">
            <h3>Enterprise</h3>
            <div className="price">Custom</div>
            <p className="period">For teams</p>
            <ul className="features">
              <li>✓ Unlimited everything</li>
              <li>✓ White-label option</li>
              <li>✓ Custom integrations</li>
              <li>✓ Priority support</li>
              <li>✓ SLA guarantee</li>
            </ul>
            <button className="btn-pricing">Contact Sales</button>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta">
        <h2>Start Automating Your Interconnection Forms Today</h2>
        <p>Join 100+ renewable energy developers saving time and money</p>
        <Link to="/queue/upload" className="btn-cta">
          ⚡ Get Started (Free)
        </Link>
      </section>

      {/* FAQ */}
      <section className="faq">
        <h2>Frequently Asked Questions</h2>
        <div className="faq-grid">
          <details className="faq-item">
            <summary>What forms does RegGuard Queue support?</summary>
            <p>
              We support FERC Form 556/557, PJM NextGen, MISO interconnection applications,
              and more. We add new forms regularly based on customer demand.
            </p>
          </details>

          <details className="faq-item">
            <summary>How accurate is the auto-fill?</summary>
            <p>
              Our AI achieves 95%+ accuracy on well-structured project data. You can always
              review and edit before submission. We flag any fields that need review.
            </p>
          </details>

          <details className="faq-item">
            <summary>Is my data secure?</summary>
            <p>
              Yes. We use enterprise-grade encryption, never store raw documents, and comply
              with GDPR and SOC 2. Your data is never shared with third parties.
            </p>
          </details>

          <details className="faq-item">
            <summary>Can I integrate with my existing systems?</summary>
            <p>
              Pro and Enterprise customers get API access. We support webhooks, batch processing,
              and custom integrations with your project management tools.
            </p>
          </details>

          <details className="faq-item">
            <summary>What if the form isn't filled correctly?</summary>
            <p>
              Our editor lets you fix any field before downloading. We also provide detailed
              accuracy reports and flag fields that need your attention.
            </p>
          </details>

          <details className="faq-item">
            <summary>Can I export to other formats?</summary>
            <p>
              Pro customers can download as PDF or Excel. Enterprise customers get XML, JSON,
              and custom format exports.
            </p>
          </details>
        </div>
      </section>
    </div>
  );
};
