/**
 * RegGuard Terms of Service — required for SMS / A2P compliance
 */

import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function TermsOfServicePage() {
  const updated = 'August 8, 2026';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-purple-400 hover:text-purple-300 transition">
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <span className="text-white font-bold">RegGuard</span>
        </div>
      </header>

      <main className="px-4 py-12 sm:px-6 lg:px-8">
        <article className="max-w-3xl mx-auto text-gray-300 space-y-8">
          <div>
            <h1 className="text-4xl font-black text-white mb-3">Terms of Service</h1>
            <p className="text-sm text-gray-400">Last updated: {updated}</p>
          </div>

          <p>
            These Terms of Service (&quot;Terms&quot;) govern your use of RegGuard at{' '}
            <a className="text-purple-300 underline" href="https://app.regguardagent.com">
              app.regguardagent.com
            </a>{' '}
            and related services (the &quot;Service&quot;). By using RegGuard, you agree to these Terms.
          </p>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">The Service</h2>
            <p>
              RegGuard provides AI-assisted research and summaries related to construction permitting,
              codes, fees, and site diligence. Outputs are informational research aids for contractors
              and related professionals. RegGuard is not a law firm, engineering firm, surveying firm,
              or licensed design professional, and does not provide legal advice.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Accounts and eligibility</h2>
            <p>
              You must provide accurate information when using the Service. You are responsible for
              activity under your account and for keeping login credentials confidential. You must be
              able to form a binding contract under applicable law to use paid features.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">SMS consent</h2>
            <p>
              By submitting your mobile phone number and requesting text delivery, you consent to receive
              SMS messages from RegGuard about your research request and related account/status updates.
              Message frequency varies. Message and data rates may apply. Reply <strong className="text-white">STOP</strong> to
              opt out and <strong className="text-white">HELP</strong> for help. Consent to SMS is not a condition of
              purchasing RegGuard services where alternatives (such as email) are available.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Fees and payments</h2>
            <p>
              Paid plans and one-time purchases are described at checkout or on the pricing page.
              Fees are charged through our payment processor. Except where required by law or expressly
              stated otherwise, payments are non-refundable once research delivery has begun or digital
              results have been made available.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Acceptable use</h2>
            <ul className="list-disc ml-5 space-y-2">
              <li>Do not misuse the Service, attempt unauthorized access, or disrupt operations</li>
              <li>Do not use RegGuard for unlawful purposes or to send spam</li>
              <li>Do not scrape, reverse engineer, or resell the Service without written permission</li>
              <li>Do not submit content you do not have the right to use</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">No warranties; research limitations</h2>
            <p>
              The Service and all outputs are provided &quot;as is&quot; and &quot;as available.&quot;
              Municipal rules, fees, and requirements change and may be incomplete in public sources.
              Always verify critical decisions with the Authority Having Jurisdiction (AHJ), licensed
              professionals, and primary source documents before bidding, filing, or building.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Limitation of liability</h2>
            <p>
              To the maximum extent permitted by law, RegGuard and its operators are not liable for
              indirect, incidental, special, consequential, or punitive damages, or for lost profits,
              lost bids, project delays, or similar losses arising from your use of the Service.
              Our total liability for any claim relating to the Service will not exceed the amounts you
              paid to RegGuard for the Service in the three months before the claim.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Intellectual property</h2>
            <p>
              RegGuard branding, software, and site content are owned by us or our licensors.
              Subject to these Terms, we grant you a limited, non-exclusive, non-transferable license
              to use the Service for your internal business purposes. Report content delivered to you
              may be used for your projects, subject to any plan limitations.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Termination</h2>
            <p>
              We may suspend or terminate access if you violate these Terms or misuse the Service.
              You may stop using RegGuard at any time. Provisions that by their nature should survive
              (including liability limits and IP) will survive termination.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Changes to these Terms</h2>
            <p>
              We may update these Terms from time to time. The &quot;Last updated&quot; date reflects the
              latest version. Continued use after changes means you accept the updated Terms.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Contact</h2>
            <p>
              Questions about these Terms:{' '}
              <a className="text-purple-300 underline" href="mailto:support@regguardagent.com">
                support@regguardagent.com
              </a>
            </p>
            <p>
              Also see our{' '}
              <Link className="text-purple-300 underline" to="/privacy">
                Privacy Policy
              </Link>
              .
            </p>
          </section>
        </article>
      </main>
    </div>
  );
}
