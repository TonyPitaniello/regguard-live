/**
 * Vercel Edge — crawlers hitting /r/:id get the server-rendered OG sales page.
 * Humans keep the interactive SPA.
 */
const BOTS =
  /bot|crawler|spider|facebookexternalhit|Facebot|WhatsApp|Slackbot|Twitterbot|LinkedInBot|Applebot|Googlebot|bingbot|Discordbot|TelegramBot|SkypeUriPreview|Slack-ImgProxy|preview/i;

export default async function middleware(request) {
  const url = new URL(request.url);
  const match = url.pathname.match(/^\/r\/([^/]+)\/?$/);
  if (!match) return;
  const ua = request.headers.get('user-agent') || '';
  if (!BOTS.test(ua)) return;
  const api = process.env.VITE_BACKEND_ORIGIN || 'https://regguard-api.onrender.com';
  const dest = `${api.replace(/\/$/, '')}/share/${encodeURIComponent(match[1])}${url.search}`;
  return fetch(dest, { headers: { Accept: 'text/html' } });
}

export const config = {
  matcher: '/r/:path*',
};
