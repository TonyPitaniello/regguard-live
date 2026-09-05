/**
 * Prefer user-typed locality over geocoder guesses (stops Plano→Dallas/Tyler swaps).
 */

/** Soft ZIP → city for known RegGuard beachheads (TX). */
const TX_ZIP_CITY: Record<string, string> = {
  '75023': 'Plano',
  '75024': 'Plano',
  '75025': 'Plano',
  '75026': 'Plano',
  '75074': 'Plano',
  '75075': 'Plano',
  '75086': 'Plano',
  '75093': 'Plano',
  '75094': 'Plano',
  '75033': 'Frisco',
  '75034': 'Frisco',
  '75035': 'Frisco',
  '75036': 'Frisco',
  '78664': 'Round Rock',
  '78665': 'Round Rock',
  '78681': 'Round Rock',
};

export function zip5Of(zip: string): string {
  return String(zip || '').replace(/\D/g, '').slice(0, 5);
}

export function cityForTxZip(zip: string): string | null {
  const z = zip5Of(zip);
  if (TX_ZIP_CITY[z]) return TX_ZIP_CITY[z];
  if (z.startsWith('787')) return 'Austin';
  if (z.startsWith('761')) return 'Fort Worth';
  if (z.startsWith('752') || z.startsWith('753')) return 'Dallas';
  return null;
}

/**
 * Merge geocoder result with what the user typed.
 * User city / state / ZIP / street win when present; ZIP table can correct city.
 */
export function preferUserLocality(opts: {
  userStreet: string;
  userCity: string;
  userState: string;
  userZip: string;
  geoStreet?: string;
  geoCity?: string;
  geoState?: string;
  geoZip?: string;
}): { street: string; city: string; state: string; zip: string; corrected: boolean } {
  const userStreet = (opts.userStreet || '').trim();
  const userCity = (opts.userCity || '').trim();
  const userState = (opts.userState || '').trim().toUpperCase().slice(0, 2);
  const userZip = zip5Of(opts.userZip);
  const geoStreet = (opts.geoStreet || '').trim();
  const geoCity = (opts.geoCity || '').trim();
  const geoState = (opts.geoState || '').trim().toUpperCase().slice(0, 2);
  const geoZip = zip5Of(opts.geoZip || '');

  // Prefer a real street line over a unit-only fragment like "#130"
  const streetLooksWeak = (s: string) =>
    !s ||
    /^#?\d{1,6}$/.test(s) ||
    /^(apt|unit|suite|ste)\b/i.test(s) ||
    s.length < 5;

  let street = userStreet;
  if (streetLooksWeak(street) && geoStreet && !streetLooksWeak(geoStreet)) {
    street = geoStreet;
  } else if (!street && geoStreet) {
    street = geoStreet;
  }

  let zip = userZip.length === 5 ? userZip : geoZip;
  let state = userState.length === 2 ? userState : geoState;
  let city = userCity || geoCity;
  let corrected = false;

  // User ZIP is authority — never adopt a conflicting geocoder ZIP/city
  if (userZip.length === 5 && geoZip && geoZip !== userZip) {
    zip = userZip;
    corrected = true;
    const mapped = state === 'TX' || !state ? cityForTxZip(userZip) : null;
    if (mapped) {
      city = userCity || mapped;
      state = state || 'TX';
    } else if (userCity) {
      city = userCity;
    }
  } else if (userCity) {
    city = userCity;
  }

  // Soft-correct empty/wrong city from ZIP table when ZIP known
  if (zip.length === 5 && (state === 'TX' || !state)) {
    const mapped = cityForTxZip(zip);
    if (mapped) {
      if (!city || city.toLowerCase() !== mapped.toLowerCase()) {
        // Only overwrite geocoder city when user didn't type a different city
        if (!userCity || userCity.toLowerCase() === mapped.toLowerCase()) {
          if (city.toLowerCase() !== mapped.toLowerCase()) corrected = true;
          city = mapped;
        }
      }
      state = state || 'TX';
    }
  }

  return {
    street: street || geoStreet || userStreet,
    city: city || '',
    state: state || '',
    zip: zip || '',
    corrected,
  };
}
