/**
 * Hostile-buyer launch fixes — source contracts (run: npx tsx src/hostileLaunchFix.test.ts)
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

function assert(cond: unknown, msg: string) {
  if (!cond) throw new Error(msg);
}

function read(rel: string) {
  return readFileSync(join(here, rel), 'utf8');
}

{
  const voice = read('VoiceCommandSystem.tsx');
  assert(voice.includes("path === '/'"), 'mic gated to home path');
  assert(voice.includes('voiceHomeOnly'), 'voiceHomeOnly flag present');
  assert(voice.includes('if (!voiceHomeOnly)'), 'early return off home');
}

{
  const results = read('components/ResultsViewerModal.tsx');
  assert(results.includes('headerStamp'), 'HOLD badge in results header');
  assert(
    results.includes('Planning aid — not a quote, sealed bid, Phase I ESA'),
    'honesty one-liner under address',
  );
  assert(
    results.includes("getElementById('rg-executive-summary')?.scrollIntoView"),
    'demo opens on executive summary',
  );
}

{
  const loc = read('components/LocationPicker.tsx');
  assert(loc.includes('onPointerDown={markSiteFieldFocused}'), 'site card unlocks on pointer');
  assert(loc.includes('Search an address'), 'mobile-friendly address hint');
}

{
  const form = read('components/FreeTrialForm.tsx');
  assert(form.includes('onPointerDown={unlockFields}'), 'email unlocks on pointer');
  assert(form.includes('onTouchStart={unlockFields}'), 'email unlocks on touch');
  assert(form.includes('you@company.com'), 'email placeholder is company-shaped');
}

{
  const main = read('main.tsx');
  assert(main.includes('launch-20261102-mask-v47'), 'BUILD bumped for mask labels');
}

{
  const results = read('components/ResultsViewerModal.tsx');
  const share = read('pages/SharedReportPage.tsx');
  const bid = read('pages/BidDayPage.tsx');
  for (const [name, src] of [
    ['results', results],
    ['share', share],
    ['bid', bid],
  ] as const) {
    assert(!src.includes('••'), `${name} has no bullet-mask glyphs`);
  }
  assert(
    results.includes('Hidden on Free — Estimator ($79/mo) shows the percent'),
    'free contingency is a plain label',
  );
  assert(results.includes('No permit total on Free'), 'free cost box states no permit total');
  assert(results.includes('No permit total'), 'paid desk still refuses an invented permit total');
  assert(share.includes('Hidden on Free — Estimator ($79/mo) shows the percent'), 'share page label');
  assert(bid.includes('Hidden on Free'), 'bid day free row label');
}

console.log('hostileLaunchFix.test.ts: ok');
