/**
 * Public SMS opt-in evidence page for A2P / TCR reviewers.
 * No login required — shows the same consent UI used in-app.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Phone } from 'lucide-react';

const PRIVACY = 'https://app.regguardagent.com/privacy';
const TERMS = 'https://app.regguardagent.com/terms';

export default function SmsOptInPage() {
  const [phone, setPhone] = useState('');
  const [consented, setConsented] = useState(false); // MUST stay unchecked by default (30925)
  const [note, setNote] = useState('');

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!consented) {
      setNote('Check the consent box to continue (required).');
      return;
    }
    const digits = phone.replace(/\D/g, '');
    if (digits.length < 10) {
      setNote('Enter a valid US mobile number.');
      return;
    }
    setNote(
      'Demo only for reviewers: in the live app this submits from Results after a site lookup and sends transactional SMS from RegGuard / Pitaniello Perkins LLC. No message is sent from this evidence page.'
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="inline-flex items-center gap-2 text-emerald-300 text-sm">
            <ArrowLeft className="w-4 h-4" /> Home
          </Link>
          <span className="font-bold">RegGuard SMS opt-in</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-10 space-y-6">
        <div>
          <h1 className="text-3xl font-black tracking-tight">SMS opt-in (public evidence)</h1>
          <p className="text-gray-400 text-sm mt-2">
            Brand: <strong className="text-white">RegGuard / Pitaniello Perkins LLC</strong>. Use case:
            transactional account notifications (research results, Bid Risk Receipt / share links,
            order or PDF-ready notices, and optional ZIP-watch / Saved Job alerts the user enables).
          </p>
          <p className="text-gray-400 text-sm mt-2">
            This page mirrors the consent experience on Results after a lookup. No account or login is
            required to review it. Full A2P packet for carriers:{' '}
            <a className="text-emerald-300 underline" href="https://app.regguardagent.com/a2p-evidence">
              app.regguardagent.com/a2p-evidence
            </a>
            .
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-xl border-2 border-emerald-500/40 bg-emerald-500/10 p-5 space-y-4"
        >
          <label htmlFor="sms-phone" className="flex items-center gap-2 text-base font-bold text-emerald-300">
            <Phone className="w-4 h-4" />
            Mobile number
          </label>
          <input
            id="sms-phone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="(555) 123-4567"
            className="w-full px-4 py-3 bg-slate-900 border border-emerald-500/40 rounded-lg text-white"
          />

          <label className="flex items-start gap-3 text-sm text-gray-200 cursor-pointer">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4"
              checked={consented}
              onChange={(e) => setConsented(e.target.checked)}
            />
            <span>
              I agree to receive transactional text messages from RegGuard / Pitaniello Perkins LLC about
              my research request, Bid Risk Receipt or shareable report links, related order or
              PDF-ready notices, and (if I enable them) Saved Job / ZIP-watch alerts. Message frequency
              varies. Message and data rates may apply. Reply STOP to opt out; HELP for help. Consent is
              not a condition of purchase. We do not share, sell, or provide mobile numbers or messaging
              consent to third parties or affiliates for marketing.{' '}
              <a href={PRIVACY} className="text-emerald-300 underline" target="_blank" rel="noreferrer">
                Privacy Policy
              </a>
              {' · '}
              <a href={TERMS} className="text-emerald-300 underline" target="_blank" rel="noreferrer">
                Terms of Service
              </a>
              .
            </span>
          </label>

          <button
            type="submit"
            disabled={!consented}
            className="w-full sm:w-auto px-6 py-3 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-900 font-black rounded-lg"
          >
            Text me
          </button>

          {note ? <p className="text-sm text-amber-100">{note}</p> : null}
        </form>

        <section className="text-sm text-gray-400 space-y-2 border border-white/10 rounded-lg p-4">
          <h2 className="text-white font-bold text-base">How opt-in works (for reviewers)</h2>
          <ol className="list-decimal ml-5 space-y-1 text-gray-300">
            <li>User visits https://app.regguardagent.com/ and completes a site lookup.</li>
            <li>
              On Results they open the Text results (SMS) panel (same fields as this public page).
            </li>
            <li>
              They enter a US mobile number, check the consent box (unchecked by default), and tap Text
              me.
            </li>
            <li>
              RegGuard sends transactional SMS only. Frequency varies. Msg &amp; data rates may apply.
              STOP / HELP honored.
            </li>
          </ol>
          <p>
            Privacy:{' '}
            <a className="text-emerald-300 underline" href={PRIVACY}>
              {PRIVACY}
            </a>
          </p>
          <p>
            Terms:{' '}
            <a className="text-emerald-300 underline" href={TERMS}>
              {TERMS}
            </a>
          </p>
        </section>
      </main>
    </div>
  );
}
