/**
 * RegGuard Privacy Policy — required for SMS / A2P compliance
 */

import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function PrivacyPolicyPage() {
  const updated = 'August 26, 2026';

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
            <h1 className="text-4xl font-black text-white mb-3">Privacy Policy</h1>
            <p className="text-sm text-gray-400">Last updated: {updated}</p>
          </div>

          <p>
            RegGuard (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;), operated by Pitaniello Perkins LLC, provides
            construction permitting and site-research tools at{' '}
            <a className="text-purple-300 underline" href="https://app.regguardagent.com">
              app.regguardagent.com
            </a>
            . This Privacy Policy explains what information we collect, how we use it, and your choices.
            This is the privacy policy that applies to our website opt-in and SMS messaging program.
          </p>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Information we collect</h2>
            <ul className="list-disc ml-5 space-y-2">
              <li>Contact details you submit (name, email address, mobile phone number)</li>
              <li>Project details (address, trade/project type, and related research inputs)</li>
              <li>Account and billing information needed to process paid orders</li>
              <li>Usage data such as pages visited, device/browser type, and basic analytics</li>
              <li>Communications you send us (support requests, feedback)</li>
              <li>
                Messaging consent records when you enter a mobile number in the RegGuard app and request
                SMS delivery (for example, by tapping &quot;Text me&quot;)
              </li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">How we use information</h2>
            <ul className="list-disc ml-5 space-y-2">
              <li>To run research, deliver reports, and operate the RegGuard service</li>
              <li>
                To send transactional email or SMS you request (research results, Bid Risk Receipt /
                share links, order or PDF-ready notices, and related account status)
              </li>
              <li>To process payments, prevent fraud, and provide customer support</li>
              <li>To improve product reliability, security, and user experience</li>
              <li>To comply with legal obligations</li>
            </ul>
          </section>

          <section id="sms" className="space-y-3">
            <h2 className="text-2xl font-bold text-white">SMS / text messaging program</h2>
            <p>
              If you provide a mobile number in the RegGuard web app and request SMS (for example, by
              entering your number and clicking &quot;Text me&quot; after a site lookup), you consent to
              receive transactional text messages from RegGuard / Pitaniello Perkins LLC about that
              research request, Bid Risk Receipt or shareable report links, and related order or
              PDF-ready notices.
            </p>
            <ul className="list-disc ml-5 space-y-2">
              <li>
                <strong className="text-white">Message frequency varies</strong> based on how often you
                request SMS delivery in the app.
              </li>
              <li>
                <strong className="text-white">Message and data rates may apply.</strong>
              </li>
              <li>
                Reply <strong className="text-white">STOP</strong> to opt out of SMS at any time. Reply{' '}
                <strong className="text-white">HELP</strong> for help.
              </li>
              <li>Consent to receive SMS is not a condition of purchasing RegGuard services.</li>
            </ul>
            <p className="font-semibold text-white">
              We do not share, sell, or provide your mobile phone number or messaging consent data to
              third parties or affiliates for marketing or promotional purposes.
            </p>
            <p>
              We may use operational service providers that help us deliver messages you requested
              (for example, our SMS gateway). Those providers process your number only to send the
              messages you asked for and are not permitted to use your mobile information or messaging
              consent for their own marketing.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">How we share information</h2>
            <p>We share information only as needed to operate the service, including with:</p>
            <ul className="list-disc ml-5 space-y-2">
              <li>Service providers (hosting, email, SMS delivery, payment processing, analytics)</li>
              <li>Professional advisors or authorities when required by law</li>
              <li>Successors in connection with a merger, acquisition, or asset sale</li>
            </ul>
            <p>
              We do not sell personal information. Separately, and specifically for SMS:{' '}
              <strong className="text-white">
                we do not share, sell, or provide your mobile phone number or messaging consent data to
                third parties or affiliates for marketing or promotional purposes.
              </strong>
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Data retention</h2>
            <p>
              We retain information for as long as needed to provide the service, maintain business records,
              resolve disputes, and meet legal requirements. You may request deletion of your personal data
              subject to applicable law and legitimate retention needs.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Security</h2>
            <p>
              We use reasonable administrative, technical, and organizational measures to protect personal
              information. No method of transmission or storage is 100% secure.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Your choices</h2>
            <ul className="list-disc ml-5 space-y-2">
              <li>Opt out of SMS by replying STOP</li>
              <li>
                Unsubscribe from marketing emails via the link in those emails (transactional messages may
                still be sent)
              </li>
              <li>Request access, correction, or deletion by contacting us</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Children</h2>
            <p>
              RegGuard is not directed to children under 13, and we do not knowingly collect their personal
              information.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Changes</h2>
            <p>
              We may update this Privacy Policy from time to time. The &quot;Last updated&quot; date at the top
              reflects the latest revision. Continued use of RegGuard after changes means you accept the
              updated policy.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-2xl font-bold text-white">Contact</h2>
            <p>
              Questions about this Privacy Policy or your data:{' '}
              <a className="text-purple-300 underline" href="mailto:support@regguardagent.com">
                support@regguardagent.com
              </a>
            </p>
            <p>
              Also see our{' '}
              <Link className="text-purple-300 underline" to="/terms">
                Terms of Service
              </Link>
              .
            </p>
          </section>
        </article>
      </main>
    </div>
  );
}
