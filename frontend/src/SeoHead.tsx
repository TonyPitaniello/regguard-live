import { useEffect } from 'react';

/** Per-route title + description for SPA SEO (crawlers that execute JS). */
export function SeoHead({
  title,
  description,
  canonical,
}: {
  title: string;
  description: string;
  canonical?: string;
}) {
  useEffect(() => {
    document.title = title;
    const ensure = (attr: string, key: string, value: string, prop = false) => {
      const sel = prop ? `meta[property="${key}"]` : `meta[${attr}="${key}"]`;
      let el = document.head.querySelector(sel) as HTMLMetaElement | null;
      if (!el) {
        el = document.createElement('meta');
        if (prop) el.setAttribute('property', key);
        else el.setAttribute(attr, key);
        document.head.appendChild(el);
      }
      el.setAttribute('content', value);
    };
    ensure('name', 'description', description);
    ensure('property', 'og:title', title, true);
    ensure('property', 'og:description', description, true);
    if (canonical) {
      ensure('property', 'og:url', canonical, true);
      let link = document.head.querySelector('link[rel="canonical"]') as HTMLLinkElement | null;
      if (!link) {
        link = document.createElement('link');
        link.rel = 'canonical';
        document.head.appendChild(link);
      }
      link.href = canonical;
    }
  }, [title, description, canonical]);
  return null;
}
