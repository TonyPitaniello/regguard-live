/**
 * OrdersPage.tsx
 * Phase 2 Week 2: Order history and PDF download portal
 * 
 * Shows user's orders and provides PDF download links
 */

import React, { useState, useEffect } from 'react';
import { Download, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { backendUrl } from '../env';

interface PDF {
  type: 'research_memo' | 'punch_list' | 'permits';
  name: string;
  size: string;
  url: string;
  icon: string;
}

interface Order {
  order_id: string;
  trial_id: string;
  tier: string;
  status: string;
  created_at: string;
  amount: number;
  pdfs: PDF[];
  expires_at: string;
  download_token?: string;
  pdf_status?: string;
  coverage_note?: string;
}

function tierLabel(tier: string): string {
  switch ((tier || '').toLowerCase()) {
    case 'partner':
      return 'Partner';
    case 'contractor_pro':
      return 'Contractor Pro';
    case 'ic_project':
    case 'ic_consultant':
      return 'IC Project Report';
    case 'ic_annual':
      return 'IC Annual';
    case 'sponsor':
      return 'Sponsor';
    default:
      return tier || 'Order';
  }
}

function isIcTier(tier: string): boolean {
  const t = (tier || '').toLowerCase();
  return t === 'ic_project' || t === 'ic_consultant' || t === 'ic_annual';
}

function pdfIsPreparing(pdf: PDF): boolean {
  const name = (pdf.name || '').toLowerCase();
  const url = (pdf.url || '').trim();
  const status = ((pdf as PDF & { status?: string }).status || '').toLowerCase();
  return (
    name.includes('preparing') ||
    status === 'preparing' ||
    !url ||
    url.includes('sample-report')
  );
}

function orderPdfsPreparing(order: Order): boolean {
  if (!isIcTier(order.tier)) return false;
  if (!order.pdfs || order.pdfs.length === 0) return true;
  return order.pdfs.some(pdfIsPreparing);
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [userEmail, setUserEmail] = useState(
    () => (typeof window !== 'undefined' ? sessionStorage.getItem('userEmail') || '' : '')
  );
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    void bootstrapOrders();
  }, []);

  // Poll while IC PDFs are still preparing (after research generates them)
  useEffect(() => {
    const needsPoll = orders.some(orderPdfsPreparing);
    if (!needsPoll || !userEmail) return;
    let n = 0;
    const id = window.setInterval(() => {
      n += 1;
      if (n > 12) {
        window.clearInterval(id);
        return;
      }
      void refreshOrdersQuiet(userEmail);
    }, 5000);
    return () => window.clearInterval(id);
  }, [orders, userEmail]);

  const refreshOrdersQuiet = async (email: string) => {
    try {
      const response = await fetch(
        backendUrl(`/orders?email=${encodeURIComponent(email)}`)
      );
      if (!response.ok) return;
      const data = await response.json();
      setOrders(data.orders || []);
    } catch {
      /* ignore poll errors */
    }
  };

  const bootstrapOrders = async () => {
    try {
      setLoading(true);
      setError('');

      const params = new URLSearchParams(window.location.search);
      const sessionId = params.get('session_id') || '';

      // After Stripe redirect: confirm session → create order even if webhook lagged
      if (sessionId) {
        const confirmRes = await fetch(
          backendUrl(`/checkout/confirm?session_id=${encodeURIComponent(sessionId)}`)
        );
        if (confirmRes.ok) {
          const confirmData = await confirmRes.json();
          const emailFromSession = (confirmData.email || '').trim().toLowerCase();
          if (emailFromSession) {
            sessionStorage.setItem('userEmail', emailFromSession);
            setUserEmail(emailFromSession);
          }
          if (confirmData.order?.tier) {
            sessionStorage.setItem('regguardPaid', '1');
            sessionStorage.setItem('regguardTier', String(confirmData.order.tier));
          } else {
            sessionStorage.setItem('regguardPaid', '1');
          }
          sessionStorage.setItem('pendingDeepUnlock', '1');
          setConfirmed(true);
        } else {
          const detail = await confirmRes.json().catch(() => ({}));
          console.warn('Checkout confirm failed', detail);
        }
      }

      const email = (
        sessionStorage.getItem('userEmail') ||
        userEmail ||
        ''
      ).trim().toLowerCase();
      if (email && email !== userEmail) setUserEmail(email);

      if (!email) {
        setOrders([]);
        setError('No email on file for this checkout. Open the link from the email you used at payment.');
        return;
      }

      const response = await fetch(
        backendUrl(`/orders?email=${encodeURIComponent(email)}`)
      );

      if (!response.ok) throw new Error('Failed to fetch orders');

      const data = await response.json();
      setOrders(data.orders || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load orders';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const downloadPDF = (pdf: PDF) => {
    // Open PDF in new tab (browser handles download)
    window.open(pdf.url, '_blank');
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getDaysRemaining = (expiresAt: string) => {
    const now = new Date();
    const expiry = new Date(expiresAt);
    const days = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return Math.max(0, days);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <p className="text-gray-300">Loading your orders...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-black text-white">My Orders</h1>
          <p className="text-gray-400 mt-1">{userEmail}</p>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {confirmed && orders.length > 0 && (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 bg-emerald-500/20 border border-emerald-500/30 rounded-lg mb-8">
            <div className="flex gap-3">
              <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div className="text-emerald-100">
                <p>Payment confirmed — your order is below.</p>
                <p className="mt-2 text-sm text-emerald-200/90">
                  Next: unlock deeper research on your site (same email).{' '}
                  {orders.some(orderPdfsPreparing)
                    ? 'IC Project PDFs generate after that confirmed lookup.'
                    : 'Contractor Pro deep scout results appear in the results window.'}
                </p>
                {orders
                  .filter((o) => isIcTier(o.tier) && o.download_token)
                  .slice(0, 1)
                  .map((o) => (
                    <div
                      key={o.order_id}
                      className="mt-3 rounded-lg border border-emerald-400/40 bg-slate-950/40 p-3"
                    >
                      <p className="text-xs font-bold uppercase tracking-wide text-emerald-300">
                        IC access code
                      </p>
                      <p className="mt-1 font-mono text-lg text-white break-all select-all">
                        {o.download_token}
                      </p>
                      <p className="mt-1 text-xs text-emerald-200/80">
                        Save this code. Check spam for the confirmation email with the same code.
                      </p>
                    </div>
                  ))}
              </div>
            </div>
            <a
              href={`/?unlock=1${userEmail ? `&email=${encodeURIComponent(userEmail)}` : ''}`}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-lg text-center whitespace-nowrap"
              onClick={() => {
                try {
                  sessionStorage.setItem('pendingDeepUnlock', '1');
                  sessionStorage.setItem('regguardPaid', '1');
                } catch {
                  /* ignore */
                }
              }}
            >
              Unlock deeper results
            </a>
          </div>
        )}

        {orders.some(orderPdfsPreparing) && (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 bg-blue-500/15 border border-blue-500/30 rounded-lg mb-8">
            <div className="flex gap-3">
              <Clock className="w-5 h-5 text-blue-300 flex-shrink-0 mt-0.5" />
              <p className="text-blue-100 text-sm">
                IC Project PDFs are preparing. Run a site lookup (same email) to generate them —
                this page refreshes automatically.
              </p>
            </div>
            <a
              href={`/${userEmail ? `?email=${encodeURIComponent(userEmail)}` : ''}`}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg text-center whitespace-nowrap"
            >
              Run site lookup
            </a>
          </div>
        )}

        {orders.some((o) => (o.tier || '').toLowerCase() === 'partner') &&
          !orders.some((o) => (o.tier || '').toLowerCase() === 'contractor_pro') && (
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 bg-emerald-500/10 border border-emerald-500/25 rounded-lg mb-8">
              <p className="text-emerald-100 text-sm">
                On Partner? Upgrade to Contractor Pro ($149/mo) if you run your own bid-week sites.
              </p>
              <a
                href={`/checkout/contractor_pro${userEmail ? `?email=${encodeURIComponent(userEmail)}` : ''}`}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-lg text-center whitespace-nowrap"
              >
                Upgrade to Pro
              </a>
            </div>
          )}

        {orders.some((o) => (o.tier || '').toLowerCase() === 'contractor_pro') && (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 bg-teal-500/10 border border-teal-500/25 rounded-lg mb-8">
            <p className="text-teal-100 text-sm">
              Prefer a lighter plan? Switch to Partner ($79/mo) for client screening — cancel Pro in
              Stripe email receipts if you already subscribed, then start Partner here.
            </p>
            <a
              href={`/checkout/partner${userEmail ? `?email=${encodeURIComponent(userEmail)}` : ''}`}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold rounded-lg text-center whitespace-nowrap"
            >
              Switch to Partner $79
            </a>
          </div>
        )}

        {error && (
          <div className="flex gap-3 p-4 bg-red-500/20 border border-red-500/30 rounded-lg mb-8">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-red-200">{error}</p>
          </div>
        )}

        {orders.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">No Orders Yet</h2>
            <p className="text-gray-400 mb-6">
              You haven't purchased any plans yet.
            </p>
            <a
              href="/free-trial"
              className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-lg hover:shadow-lg transition inline-block"
            >
              Start Free Trial
            </a>
          </div>
        ) : (
          <div className="space-y-6">
            {orders.map((order) => (
              <OrderCard
                key={order.order_id}
                order={order}
                onDownload={downloadPDF}
                formatDate={formatDate}
                getDaysRemaining={getDaysRemaining}
                tierLabel={tierLabel}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

// ============================================================================
// ORDER CARD COMPONENT
// ============================================================================

function OrderCard({
  order,
  onDownload,
  formatDate,
  getDaysRemaining,
  tierLabel,
}: {
  order: Order;
  onDownload: (pdf: PDF) => void;
  formatDate: (date: string) => string;
  getDaysRemaining: (date: string) => number;
  tierLabel: (tier: string) => string;
}) {
  const daysRemaining = getDaysRemaining(order.expires_at);
  const tierColors = {
    free: 'from-gray-500 to-slate-500',
    premium: 'from-blue-600 to-purple-600',
    enterprise: 'from-indigo-600 to-purple-600',
    contractor_pro: 'from-emerald-600 to-green-600',
    ic_project: 'from-blue-600 to-indigo-600',
    ic_consultant: 'from-blue-600 to-indigo-600',
  };

  const tierColor = tierColors[order.tier as keyof typeof tierColors] || tierColors.premium;

  return (
    <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-purple-500/20 rounded-lg overflow-hidden hover:border-purple-500/40 transition">
      {/* Header */}
      <div className={`bg-gradient-to-r ${tierColor} p-6`}>
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-2xl font-bold text-white">
                {tierLabel(order.tier)}
              </h2>
              <span
                className={`px-3 py-1 rounded text-sm font-semibold ${
                  order.status === 'completed'
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-yellow-500/20 text-yellow-400'
                }`}
              >
                {order.status === 'completed' ? '✓ Completed' : 'Pending'}
              </span>
            </div>
            <p className="text-sm text-gray-200">
              Order #{order.order_id.slice(0, 8)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-black text-white">${(order.amount / 100).toLocaleString()}</p>
            <p className="text-sm text-gray-300">Purchased {formatDate(order.created_at)}</p>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          {/* Order Info */}
          <div>
            <h3 className="text-sm font-bold text-gray-400 uppercase mb-4">
              Order Information
            </h3>
            <dl className="space-y-3">
              <div>
                <dt className="text-sm text-gray-500">Status</dt>
                <dd className="text-white font-semibold flex items-center gap-2">
                  {order.status === 'completed' ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-green-400" />
                      Completed
                    </>
                  ) : (
                    <>
                      <Clock className="w-4 h-4 text-yellow-400" />
                      Processing
                    </>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Access Expires</dt>
                <dd className="text-white font-semibold">
                  {formatDate(order.expires_at)}
                  {daysRemaining < 7 && (
                    <span className="text-xs text-orange-400 ml-2">
                      ({daysRemaining} days left)
                    </span>
                  )}
                </dd>
              </div>
              {isIcTier(order.tier) && order.download_token ? (
                <div>
                  <dt className="text-sm text-gray-500">IC access code</dt>
                  <dd className="text-emerald-300 font-mono text-sm break-all select-all mt-1">
                    {order.download_token}
                  </dd>
                </div>
              ) : null}
            </dl>
          </div>

          {/* Download Info */}
          <div>
            <h3 className="text-sm font-bold text-gray-400 uppercase mb-4">
              Included Files
            </h3>
            <ul className="space-y-2 text-sm text-gray-300">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                Research Memo PDF
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                Complete Punch List
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                State Permit Package
              </li>
            </ul>
          </div>
        </div>

        {/* Download Buttons */}
        {order.status === 'completed' && order.pdfs && order.pdfs.length > 0 ? (
          <div>
            <h3 className="text-sm font-bold text-gray-400 uppercase mb-4">
              Download Files
            </h3>
            {orderPdfsPreparing(order) ? (
              <div className="p-4 bg-slate-700/40 border border-slate-600/40 rounded-lg mb-4">
                <p className="text-gray-300 text-sm">
                  PDFs generate after you run a site lookup with the same email used at checkout.
                  Planning diligence package — confirm fees and filings with the AHJ before bid.
                </p>
                <a
                  href="/"
                  className="inline-block mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg"
                  onClick={(e) => {
                    const email =
                      (typeof window !== 'undefined' && sessionStorage.getItem('userEmail')) || '';
                    if (email) {
                      e.preventDefault();
                      window.location.href = `/?email=${encodeURIComponent(email)}`;
                    }
                  }}
                >
                  Run site lookup →
                </a>
              </div>
            ) : null}
            <div className="grid sm:grid-cols-3 gap-3">
              {order.pdfs.map((pdf) => {
                const preparing = pdfIsPreparing(pdf);
                return (
                  <button
                    key={pdf.type}
                    onClick={() => !preparing && onDownload(pdf)}
                    disabled={preparing}
                    className={`flex items-center justify-center gap-2 px-4 py-3 border rounded-lg transition font-semibold ${
                      preparing
                        ? 'bg-slate-700/40 border-slate-600/40 text-gray-500 cursor-not-allowed'
                        : 'bg-purple-600/20 hover:bg-purple-600/30 border-purple-500/30 hover:border-purple-500/50 text-purple-300 hover:text-purple-200'
                    }`}
                  >
                    <Download className="w-4 h-4" />
                    <span className="truncate">{pdf.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="p-4 bg-slate-700/30 border border-slate-600/30 rounded-lg text-center">
            <p className="text-gray-400 text-sm">
              Run a site lookup with your purchase email to generate downloadable PDFs.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
