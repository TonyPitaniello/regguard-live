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
            <h3>Your review</h3>
            <p>You stay in control — nothing is filed without you</p>
          </div>
          <div className="benefit">
            <div className="benefit-icon">♻️</div>
            <h3>Reusable Templates</h3>
            <p>Save company info for future applications</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta">
        <h2>Try the interconnection form draft demo</h2>
        <p>
          Preview only — not a live RTO filing product. For citeable site diligence PDFs,
          use Reg Guard IC Project Report or Contractor Pro.
        </p>
        <Link to="/queue/upload" className="btn-cta">
          Open demo auto-fill
        </Link>
        <p style={{ marginTop: '1rem' }}>
          <Link to="/checkout/ic_project" style={{ color: 'inherit', textDecoration: 'underline' }}>
            View IC Project Report
          </Link>
        </p>
      </section>

      {/* FAQ */}
      <section className="faq">
        <h2>Demo FAQ</h2>
        <div className="faq-grid">
          <details className="faq-item">
            <summary>Does this file with an RTO?</summary>
            <p>
              No. This is a draft helper for common interconnection form layouts. Official
              filing, fees, and queue position stay on the RTO portal.
            </p>
          </details>

          <details className="faq-item">
            <summary>How should I treat auto-filled fields?</summary>
            <p>
              Treat every field as unverified until you check it. Download drafts are for
              your records and prep — not an official submittal package.
            </p>
          </details>

          <details className="faq-item">
            <summary>Where do I get a paid diligence report?</summary>
            <p>
              Use Contractor Pro or IC Project Report for citeable site diligence PDFs
              (planning worksheets — confirm fees and filings with the local AHJ).
            </p>
          </details>
        </div>
      </section>
    </div>
  );
};
