/**
 * LocationPicker — type street/city/state/ZIP → map pin (forward geocode),
 * or click map / Places / Auto-Detect. No Manual Entry gate required.
 */

import { useState, useEffect, useRef, type CSSProperties, type ChangeEvent } from 'react';
import { MapPin, Navigation, AlertCircle, CheckCircle2 } from 'lucide-react';
import { backendUrl } from '../env';
import {
  AddressAutocomplete,
  mapsAutocompleteEnabled,
  type AddressSelection,
} from '../AddressAutocomplete';
import { preferUserLocality, zip5Of, cityForTxZip } from '../addressPrefer';

function isWeakStreetLine(s: string): boolean {
  const t = (s || '').trim();
  if (!t) return true;
  if (/^#?\d{1,6}[A-Za-z]?$/.test(t)) return true;
  if (/^(apt|apartment|unit|suite|ste|fl|floor|bldg|building)\b/i.test(t)) return true;
  if (t.length < 5) return true;
  return false;
}

/** Pull a usable street from a Places formatted line (skip unit-only first segment). */
function streetFromFormatted(formatted: string): string {
  const parts = (formatted || '')
    .split(',')
    .map((p) => p.trim())
    .filter(Boolean);
  for (const p of parts) {
    if (isWeakStreetLine(p)) continue;
    if (/^[A-Z]{2}$/i.test(p)) continue;
    if (/^\d{5}(-\d{4})?$/.test(p)) continue;
    if (/^(TX|Texas|USA|United States)$/i.test(p)) continue;
    return p;
  }
  return '';
}

interface LocationPickerProps {
  onLocationSelect: (
    address: string,
    city: string,
    state: string,
    zip: string,
    lat: number,
    lng: number
  ) => void;
  disabled?: boolean;
  /** When true (e.g. results modal open), hide/destroy the map so it cannot float over the page */
  collapseMap?: boolean;
  /** Voice fill / parent-driven address fields */
  externalValues?: {
    address?: string;
    city?: string;
    state?: string;
    zip?: string;
  } | null;
  /** Bump to force clear of local pin/fields (New site) */
  resetKey?: number;
}

const MAP_SHELL_STYLE: CSSProperties = {
  position: 'relative',
  zIndex: 0,
  overflow: 'hidden',
  isolation: 'isolate',
  // Do NOT use contain:layout/paint — Leaflet tiles go blank after Auto-Detect / remount.
  transform: 'none',
  WebkitTransform: 'none',
  minHeight: '20rem',
  background: '#334155',
};

function parseStateZip(formatted: string): { state: string; zip: string } {
  const m = formatted.match(/\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\b/);
  if (!m) return { state: '', zip: '' };
  return { state: m[1], zip: m[2] };
}

function composeQuery(street: string, city: string, state: string, zip: string): string {
  const zip5 = zip.replace(/\D/g, '').slice(0, 5);
  const st = state.trim().toUpperCase().slice(0, 2);
  const tail = [st, zip5].filter(Boolean).join(' ');
  return [street.trim(), city.trim(), tail].filter(Boolean).join(', ');
}

function addressReadyForGeocode(street: string, city: string, state: string, zip: string): boolean {
  const zip5 = zip.replace(/\D/g, '').slice(0, 5);
  const st = state.trim();
  const hasStreet = street.trim().length >= 3;
  if (!hasStreet) return false;
  if (zip5.length === 5) return true;
  return Boolean(city.trim() && st.length >= 2);
}

export function LocationPicker({
  onLocationSelect,
  disabled = false,
  collapseMap = false,
  externalValues = null,
  resetKey = 0,
}: LocationPickerProps) {
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [zip, setZip] = useState('');
  const [lat, setLat] = useState<number | null>(null);
  const [lng, setLng] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mapVisible, setMapVisible] = useState(true);
  /** Bump to force Leaflet re-init when the shell remounts (fixes gray blank map). */
  const [mapEpoch, setMapEpoch] = useState(0);
  const [locationConfirmed, setLocationConfirmed] = useState(false);
  /** Unlock after focus so Chrome cannot autofill jobsite on hard refresh */
  const [siteFieldsUnlocked, setSiteFieldsUnlocked] = useState(false);
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const latLngRef = useRef<{ lat: number; lng: number } | null>(null);
  /** Last query we already resolved (forward / reverse / places) — avoids geocode loops. */
  const settledQueryRef = useRef('');
  const forwardAbortRef = useRef<AbortController | null>(null);
  /** While > now, blank autofill paint is purged (cancelled on site-field focus). */
  const autofillPurgeUntilRef = useRef(0);
  /**
   * Chrome/Safari contact autofill often writes home street/city/ZIP when the user
   * fills phone/email. Ignore site-field onChange unless a site input actually has focus.
   */
  const siteFieldFocusedRef = useRef(false);

  const destroyMap = () => {
    if (mapRef.current) {
      try {
        const ro = (mapRef.current as { __rgRo?: ResizeObserver }).__rgRo;
        ro?.disconnect();
      } catch {
        /* ignore */
      }
      try {
        mapRef.current.off();
        mapRef.current.remove();
      } catch {
        /* ignore teardown races */
      }
      mapRef.current = null;
    }
    markerRef.current = null;
  };

  // Sync voice-fill / external parent values into local fields → forward geocode
  useEffect(() => {
    if (!externalValues) return;
    const nextAddress = externalValues.address ?? '';
    const nextCity = externalValues.city ?? '';
    const nextState = externalValues.state ?? '';
    const nextZip = externalValues.zip ?? '';
    if (!nextAddress && !nextCity && !nextState && !nextZip) return;
    autofillPurgeUntilRef.current = 0; // do not wipe checkout / voice restore
    settledQueryRef.current = ''; // allow forward geocode
    if (nextAddress) setAddress(nextAddress);
    if (nextCity) setCity(nextCity);
    if (nextState) setState(nextState);
    if (nextZip) setZip(nextZip);
    setSiteFieldsUnlocked(true);
    setMapVisible(true);
    setLocationConfirmed(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    externalValues?.address,
    externalValues?.city,
    externalValues?.state,
    externalValues?.zip,
  ]);

  // Parent "New site" / hard refresh — wipe local pin state
  useEffect(() => {
    settledQueryRef.current = '';
    setAddress('');
    setCity('');
    setState('');
    setZip('');
    setLat(null);
    setLng(null);
    latLngRef.current = null;
    setLocationConfirmed(false);
    setError('');
    setMapVisible(true);
    setSiteFieldsUnlocked(false);
    destroyMap();
    autofillPurgeUntilRef.current = Date.now() + 700;
    const purge = () => {
      if (Date.now() > autofillPurgeUntilRef.current) return;
      if (siteFieldFocusedRef.current) return;
      setAddress('');
      setCity('');
      setState('');
      setZip('');
    };
    const t1 = window.setTimeout(purge, 50);
    const t2 = window.setTimeout(purge, 350);
    const t3 = window.setTimeout(purge, 700);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey]);

  const unlockPin = () => {
    settledQueryRef.current = '';
    setLocationConfirmed(false);
    setError('Pin unlocked — edit the address or move the map, then confirm again.');
  };

  const clearSite = () => {
    settledQueryRef.current = '';
    setAddress('');
    setCity('');
    setState('');
    setZip('');
    setLat(null);
    setLng(null);
    latLngRef.current = null;
    setLocationConfirmed(false);
    setSiteFieldsUnlocked(false);
    setError('');
    setMapVisible(true);
    destroyMap();
    setMapEpoch((e) => e + 1);
  };

  useEffect(() => {
    if (collapseMap) destroyMap();
  }, [collapseMap]);

  useEffect(() => () => {
    destroyMap();
    forwardAbortRef.current?.abort();
  }, []);

  const refreshMapView = (latitude?: number, longitude?: number) => {
    const map = mapRef.current;
    if (!map) return;
    const kick = () => {
      try {
        map.invalidateSize({ animate: false });
        if (
          latitude != null &&
          longitude != null &&
          Number.isFinite(latitude) &&
          Number.isFinite(longitude)
        ) {
          map.setView([latitude, longitude], Math.max(map.getZoom() || 13, 13), {
            animate: false,
          });
        }
      } catch {
        /* ignore */
      }
    };
    kick();
    window.requestAnimationFrame(kick);
    window.setTimeout(kick, 50);
    window.setTimeout(kick, 250);
    window.setTimeout(kick, 600);
  };

  const placeMarker = (latitude: number, longitude: number) => {
    const L = (window as any).L;
    const map = mapRef.current;
    if (!L || !map) return;
    // If React remounted the shell, Leaflet still points at a detached node → gray box
    try {
      if (mapContainer.current && map.getContainer() !== mapContainer.current) {
        destroyMap();
        setMapEpoch((n) => n + 1);
        return;
      }
    } catch {
      destroyMap();
      setMapEpoch((n) => n + 1);
      return;
    }
    if (markerRef.current) {
      try {
        map.removeLayer(markerRef.current);
      } catch {
        /* ignore */
      }
    }
    markerRef.current = L.marker([latitude, longitude], { title: 'Selected Location' }).addTo(map);
    refreshMapView(latitude, longitude);
  };

  const commitPin = (
    latitude: number,
    longitude: number,
    street: string,
    nextCity: string,
    nextState: string,
    nextZip: string,
    syncParent: boolean
  ) => {
    latLngRef.current = { lat: latitude, lng: longitude };
    setLat(latitude);
    setLng(longitude);
    setMapVisible(true);
    placeMarker(latitude, longitude);
    settledQueryRef.current = composeQuery(street, nextCity, nextState, nextZip);
    // Never auto-lock — locking is opt-in via "Lock pin"
    setLocationConfirmed(false);
    if (syncParent && street && nextCity && nextState && nextZip.length === 5) {
      onLocationSelect(street, nextCity, nextState, nextZip, latitude, longitude);
      setError('');
    }
  };

  const reverseGeocode = async (latitude: number, longitude: number) => {
    setLoading(true);
    setError('');
    setLocationConfirmed(false);
    try {
      const q = new URLSearchParams({
        latitude: String(latitude),
        longitude: String(longitude),
      });
      const controller = new AbortController();
      const t = window.setTimeout(() => controller.abort(), 15000);
      const res = await fetch(`${backendUrl('/reverse-geocode-address')}?${q}`, {
        cache: 'no-store',
        signal: controller.signal,
      });
      window.clearTimeout(t);

      if (!res.ok) {
        let detail = 'Could not read that map pin — fill city / state / ZIP below, then confirm.';
        try {
          const body = await res.json();
          if (typeof body?.detail === 'string' && body.detail.trim()) detail = body.detail;
        } catch {
          /* ignore */
        }
        setError(detail);
        if (!address) setAddress(`${latitude.toFixed(5)}, ${longitude.toFixed(5)}`);
        return;
      }

      const data = (await res.json()) as {
        formatted_address?: string;
        zip?: string;
        city?: string;
        state?: string;
        street?: string;
      };
      const formatted = (data.formatted_address || '').trim();
      const parsed = parseStateZip(formatted);
      const geoStreet = (data.street || formatted.split(',')[0] || '').trim();
      const geoCity = (data.city || '').trim();
      const geoState = (data.state || parsed.state || '').trim();
      const geoZip = ((data.zip || parsed.zip || '').match(/\d{5}/) || [''])[0];

      // Keep user-typed Plano / 75074 — reverse geocode must not swap to Dallas/Tyler
      const merged = preferUserLocality({
        userStreet: address,
        userCity: city,
        userState: state,
        userZip: zip,
        geoStreet,
        geoCity,
        geoState,
        geoZip,
      });

      if (!address.trim() || address.trim().length < 5) {
        setAddress(merged.street || formatted || `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`);
      }
      if (!city.trim()) setCity(merged.city);
      if (!state.trim()) setState(merged.state);
      if (zip5Of(zip).length < 5) setZip(merged.zip);

      const useStreet = address.trim().length >= 5 ? address.trim() : merged.street;
      const useCity = city.trim() || merged.city;
      const useStateVal = state.trim() || merged.state;
      const useZip = zip5Of(zip).length === 5 ? zip5Of(zip) : merged.zip;

      if (merged.corrected) {
        setError(
          `Kept your city/ZIP (${useCity || 'site'}, ${useZip}) — map pin updated. Geocoder had suggested a different city.`
        );
      }

      commitPin(
        latitude,
        longitude,
        useStreet,
        useCity,
        useStateVal,
        useZip,
        Boolean(useStreet && useCity && useStateVal && useZip.length === 5)
      );
      if (!(useStreet && useCity && useStateVal && useZip.length === 5)) {
        setError(
          'Pin set — complete any missing city / state / ZIP below, then tap Find on map if needed.'
        );
      }
    } catch {
      setError(
        'Address lookup timed out — keep the pin, fill city / state / ZIP below, then confirm.'
      );
      if (!address) setAddress(`${latitude.toFixed(5)}, ${longitude.toFixed(5)}`);
    } finally {
      setLoading(false);
    }
  };

  const applyPin = async (latitude: number, longitude: number) => {
    latLngRef.current = { lat: latitude, lng: longitude };
    setLat(latitude);
    setLng(longitude);
    setMapVisible(true);
    // Defer marker until after paint so Auto-Detect does not hit a 0-size shell
    window.requestAnimationFrame(() => {
      if (!mapRef.current) {
        setMapEpoch((n) => n + 1);
      }
      placeMarker(latitude, longitude);
      refreshMapView(latitude, longitude);
    });
    await reverseGeocode(latitude, longitude);
    window.requestAnimationFrame(() => {
      if (!mapRef.current) {
        setMapEpoch((n) => n + 1);
      }
      refreshMapView(latitude, longitude);
    });
  };

  const forwardGeocodeViaMapsJs = async (
    query: string,
    bias?: { zip?: string; city?: string; state?: string }
  ): Promise<{
    street: string;
    city: string;
    state: string;
    zip: string;
    lat: number;
    lng: number;
  } | null> => {
    const g = (window as any).google?.maps;
    if (!g?.Geocoder) return null;
    try {
      const geocoder = new g.Geocoder();
      const componentRestrictions: Record<string, string> = { country: 'US' };
      const z = zip5Of(bias?.zip || '');
      if (z.length === 5) componentRestrictions.postalCode = z;
      if ((bias?.state || '').trim().length === 2) {
        componentRestrictions.administrativeArea = bias!.state!.trim().toUpperCase();
      }
      const response = await new Promise<any>((resolve, reject) => {
        geocoder.geocode(
          { address: query, componentRestrictions },
          (results: any, status: string) => {
            if (status === 'OK' && results?.[0]) resolve(results[0]);
            else reject(new Error(status || 'ZERO_RESULTS'));
          }
        );
      });
      const loc = response.geometry?.location;
      const lat = typeof loc?.lat === 'function' ? loc.lat() : Number(loc?.lat);
      const lng = typeof loc?.lng === 'function' ? loc.lng() : Number(loc?.lng);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
      const comps: any[] = response.address_components || [];
      const longOf = (...types: string[]) => {
        const hit = comps.find((c) => (c.types || []).some((t: string) => types.includes(t)));
        return (hit?.long_name || hit?.longText || '').trim();
      };
      const shortOf = (...types: string[]) => {
        const hit = comps.find((c) => (c.types || []).some((t: string) => types.includes(t)));
        return (hit?.short_name || hit?.shortText || '').trim();
      };
      const num = longOf('street_number');
      const route = longOf('route');
      const street = [num, route].filter(Boolean).join(' ') || String(response.formatted_address || '').split(',')[0];
      const city = longOf('locality') || longOf('sublocality', 'sublocality_level_1');
      const state = shortOf('administrative_area_level_1').slice(0, 2).toUpperCase();
      const zip = (longOf('postal_code').match(/\d{5}/) || [''])[0];
      return { street, city, state, zip, lat, lng };
    } catch {
      return null;
    }
  };

  const forwardGeocode = async (
    street: string,
    nextCity: string,
    nextState: string,
    nextZip: string
  ) => {
    const query = composeQuery(street, nextCity, nextState, nextZip);
    if (!addressReadyForGeocode(street, nextCity, nextState, nextZip)) return;
    if (query === settledQueryRef.current) return;

    forwardAbortRef.current?.abort();
    const controller = new AbortController();
    forwardAbortRef.current = controller;
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({
        street: street.trim(),
        city: nextCity.trim(),
        state: nextState.trim(),
        zip: nextZip.replace(/\D/g, '').slice(0, 5),
        address: query,
      });
      let data: {
        street?: string;
        city?: string;
        state?: string;
        zip?: string;
        latitude?: string;
        longitude?: string;
        formatted_address?: string;
      } | null = null;

      try {
        const res = await fetch(`${backendUrl('/geocode-address')}?${params}`, {
          cache: 'no-store',
          signal: controller.signal,
        });
        if (res.ok) {
          data = await res.json();
        }
      } catch (e: any) {
        if (e?.name === 'AbortError') return;
      }

      if (!data) {
        const viaMaps = await forwardGeocodeViaMapsJs(query, {
          zip: nextZip,
          city: nextCity,
          state: nextState,
        });
        if (viaMaps) {
          data = {
            street: viaMaps.street,
            city: viaMaps.city,
            state: viaMaps.state,
            zip: viaMaps.zip,
            latitude: String(viaMaps.lat),
            longitude: String(viaMaps.lng),
          };
        }
      }

      if (!data) {
        setError('Could not place that address on the map — check spelling or click the map.');
        setLocationConfirmed(false);
        return;
      }

      const latitude = Number(data.latitude);
      const longitude = Number(data.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        setError('Could not resolve coordinates for that address.');
        return;
      }

      const merged = preferUserLocality({
        userStreet: street,
        userCity: nextCity,
        userState: nextState,
        userZip: nextZip,
        geoStreet: data.street || data.formatted_address?.split(',')[0] || '',
        geoCity: data.city || '',
        geoState: data.state || '',
        geoZip: data.zip || '',
      });

      // Only fill blanks in the form — never overwrite Plano with Dallas
      if (!city.trim() && merged.city) setCity(merged.city);
      if (!state.trim() && merged.state) setState(merged.state);
      if (zip5Of(zip).length < 5 && merged.zip) setZip(merged.zip);
      if (street.trim().length < 5 && merged.street) setAddress(merged.street);

      if (merged.corrected) {
        setError(
          `Using ${merged.city}, ${merged.state} ${merged.zip} (your ZIP/city). Map pin placed — verify before running.`
        );
      }

      commitPin(
        latitude,
        longitude,
        merged.street,
        merged.city,
        merged.state,
        merged.zip,
        Boolean(merged.street && merged.city && merged.state && merged.zip.length === 5)
      );
    } catch (e: any) {
      if (e?.name === 'AbortError') return;
      setError('Address lookup timed out — try again or click the map.');
      setLocationConfirmed(false);
    } finally {
      if (forwardAbortRef.current === controller) {
        setLoading(false);
      }
    }
  };

  // Debounced forward geocode when user types site fields
  useEffect(() => {
    if (disabled || collapseMap) return;
    if (!addressReadyForGeocode(address, city, state, zip)) return;
    const query = composeQuery(address, city, state, zip);
    if (query === settledQueryRef.current) return;

    const t = window.setTimeout(() => {
      void forwardGeocode(address, city, state, zip);
    }, 550);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [address, city, state, zip, disabled, collapseMap]);

  const handleAutoDetect = () => {
    setLoading(true);
    setError('');
    setLocationConfirmed(false);

    if (!navigator.geolocation) {
      setError('Geolocation not supported — enter the address below or click the map.');
      setMapVisible(true);
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setMapVisible(true);
        void applyPin(position.coords.latitude, position.coords.longitude);
      },
      () => {
        setError('Location access denied — enter the address below or click the map.');
        setMapVisible(true);
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }
    );
  };

  // Initialize map once when visible (re-init if React remounted the shell)
  useEffect(() => {
    if (collapseMap || !mapVisible || !mapContainer.current) return;
    try {
      if (
        mapRef.current &&
        mapContainer.current &&
        mapRef.current.getContainer() !== mapContainer.current
      ) {
        destroyMap();
      }
    } catch {
      destroyMap();
    }
    if (mapRef.current) {
      // Already bound to this shell — still kick size (Auto-Detect / layout shifts)
      const seed = latLngRef.current;
      refreshMapView(seed?.lat ?? lat ?? undefined, seed?.lng ?? lng ?? undefined);
      return;
    }

    const initializeMap = () => {
      if (!mapContainer.current || mapRef.current) return;
      const L = (window as any).L;
      if (!L) return;
      const seed = latLngRef.current;
      const initialLat = seed?.lat ?? lat ?? 32.78;
      const initialLng = seed?.lng ?? lng ?? -96.8;

      const map = L.map(mapContainer.current, { preferCanvas: true }).setView(
        [initialLat, initialLng],
        seed || (lat && lng) ? 13 : 5
      );
      mapRef.current = map;

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
      }).addTo(map);

      if (seed || (lat != null && lng != null)) {
        placeMarker(seed?.lat ?? (lat as number), seed?.lng ?? (lng as number));
      }

      map.on('click', (e: any) => {
        const { lat: clickLat, lng: clickLng } = e.latlng;
        void applyPin(clickLat, clickLng);
      });

      refreshMapView(initialLat, initialLng);

      const el = mapContainer.current;
      if (el && typeof ResizeObserver !== 'undefined') {
        const ro = new ResizeObserver(() => refreshMapView(initialLat, initialLng));
        ro.observe(el);
        (map as { __rgRo?: ResizeObserver }).__rgRo = ro;
      }
    };

    const L = (window as any).L;
    if (L) {
      initializeMap();
      return;
    }

    if (!document.querySelector('link[data-rg-leaflet]')) {
      const cssLink = document.createElement('link');
      cssLink.rel = 'stylesheet';
      cssLink.href = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
      cssLink.setAttribute('data-rg-leaflet', '1');
      document.head.appendChild(cssLink);
    }

    const existing = document.querySelector('script[data-rg-leaflet]') as HTMLScriptElement | null;
    if (existing) {
      if ((window as any).L) initializeMap();
      else existing.addEventListener('load', () => initializeMap(), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
    script.setAttribute('data-rg-leaflet', '1');
    script.onload = () => initializeMap();
    document.body.appendChild(script);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapVisible, collapseMap, mapEpoch]);

  // Keep marker in sync after map exists
  useEffect(() => {
    if (lat == null || lng == null) return;
    if (!mapRef.current) {
      // Map may still be loading Leaflet — kick visibility so init effect can run
      setMapVisible(true);
      return;
    }
    placeMarker(lat, lng);
    refreshMapView(lat, lng);
  }, [lat, lng]);

  const handleConfirmLocation = () => {
    const zip5 = (zip || '').replace(/\D/g, '').slice(0, 5);
    if (!address.trim() || !city.trim() || !state.trim() || zip5.length !== 5) {
      setError('Fill street, city, state, and 5-digit ZIP, then place the pin.');
      return;
    }
    if (lat === null || lng === null) {
      void forwardGeocode(address, city, state, zip);
      setError('Placing pin on the map…');
      return;
    }
    onLocationSelect(address.trim(), city.trim(), state.trim(), zip5, lat, lng);
    settledQueryRef.current = composeQuery(address, city, state, zip5);
    // Do not lock — fields stay editable; optional Lock pin below
    setLocationConfirmed(false);
    setError('');
  };

  const lockPin = () => {
    const zip5 = (zip || '').replace(/\D/g, '').slice(0, 5);
    if (!address.trim() || !city.trim() || !state.trim() || zip5.length !== 5) {
      setError('Fill street, city, state, and ZIP before locking.');
      return;
    }
    if (lat === null || lng === null) {
      setError('Place the pin on the map first, then lock if you want.');
      return;
    }
    onLocationSelect(address.trim(), city.trim(), state.trim(), zip5, lat, lng);
    setLocationConfirmed(true);
    setError('');
  };

  const handlePlacesSelection = (sel: AddressSelection | null) => {
    if (!sel) {
      setLocationConfirmed(false);
      return;
    }
    const formatted = (sel.formattedAddress || '').trim();
    let street = (sel.street || '').trim();
    if (isWeakStreetLine(street)) {
      street = streetFromFormatted(formatted) || street;
    }
    const nextCity = (sel.city || '').trim();
    const nextState = (sel.state || '').trim();
    const nextZip = (sel.zip || '').replace(/\D/g, '').slice(0, 5);

    // Prefer already-typed locality (Plano / 75074) over a bad Places hit (Dallas / 75251)
    const merged = preferUserLocality({
      userStreet: address.trim().length >= 5 && !isWeakStreetLine(address) ? address : street,
      userCity: city,
      userState: state,
      userZip: zip,
      geoStreet: street,
      geoCity: nextCity,
      geoState: nextState,
      geoZip: nextZip,
    });

    // ZIP table wins when Places city conflicts with known beachhead ZIP the user typed
    const typedZip = zip5Of(zip);
    if (typedZip.length === 5) {
      const mapped = cityForTxZip(typedZip);
      if (mapped) {
        merged.city = mapped;
        merged.zip = typedZip;
        merged.state = (state.trim() || 'TX').toUpperCase().slice(0, 2);
      }
    }

    if (isWeakStreetLine(merged.street) && streetFromFormatted(formatted)) {
      merged.street = streetFromFormatted(formatted);
    }

    setAddress(merged.street);
    setCity(merged.city);
    setState(merged.state);
    setZip(merged.zip);

    const latitude = sel.lat;
    const longitude = sel.lng;
    if (
      latitude != null &&
      longitude != null &&
      Number.isFinite(latitude) &&
      Number.isFinite(longitude) &&
      !(Math.abs(latitude) < 1e-6 && Math.abs(longitude) < 1e-6)
    ) {
      commitPin(
        latitude,
        longitude,
        merged.street,
        merged.city,
        merged.state,
        merged.zip,
        Boolean(merged.street && merged.city && merged.state && merged.zip.length === 5)
      );
      if (isWeakStreetLine(merged.street)) {
        setError(
          'Places returned a unit-only line (e.g. #130). Type the full street (e.g. 1201 14th St) plus Plano / 75074.'
        );
        setLocationConfirmed(false);
      } else if (merged.corrected) {
        setError(`Kept ZIP/city as ${merged.city}, ${merged.zip} — verify before running.`);
      } else if (!(merged.street && merged.city && merged.state && merged.zip.length === 5)) {
        setError('Address found — complete city / state / ZIP, then tap Find on map if needed.');
      }
      return;
    }
    settledQueryRef.current = '';
    setLocationConfirmed(false);
    setError('Address found — complete fields so we can place the pin.');
  };

  /**
   * Chrome/Safari contact autofill often writes home street/city/ZIP when the user
   * fills phone/email. Ignore site-field onChange unless a site input actually has focus
   * (Places / map / reverse-geocode still update via setState, not this handler).
   */
  const markSiteFieldFocused = () => {
    siteFieldFocusedRef.current = true;
    autofillPurgeUntilRef.current = 0;
    setSiteFieldsUnlocked(true);
  };

  const onSiteFieldBlur = () => {
    window.setTimeout(() => {
      const ae = document.activeElement;
      if (!(ae instanceof HTMLElement) || !ae.closest('[data-rg-site-fields]')) {
        siteFieldFocusedRef.current = false;
      }
    }, 0);
  };

  const onFieldChange = (setter: (v: string) => void) => (e: ChangeEvent<HTMLInputElement>) => {
    const ae = document.activeElement;
    const focusOnThis = ae === e.currentTarget;
    const focusInSite =
      ae instanceof HTMLElement && Boolean(ae.closest('[data-rg-site-fields]'));
    if (!focusOnThis && !focusInSite && !siteFieldFocusedRef.current) {
      // Contact autofill tried to overwrite the jobsite — keep React-controlled values.
      return;
    }
    settledQueryRef.current = ''; // user edited — allow re-geocode
    setter(e.target.value);
    setLocationConfirmed(false);
  };

  const showMapUi = mapVisible && !collapseMap;
  const pinReady = lat != null && lng != null;
  const placesOn = mapsAutocompleteEnabled();

  return (
    <div className="space-y-4 relative" style={{ position: 'relative', zIndex: 0, transform: 'none' }}>
      <style>{`
        .rg-location-map-shell,
        .rg-location-map-shell .leaflet-container {
          position: relative !important;
          z-index: 0 !important;
          overflow: hidden !important;
          transform: none !important;
          -webkit-transform: none !important;
          will-change: auto !important;
        }
        .rg-location-map-shell .leaflet-pane,
        .rg-location-map-shell .leaflet-map-pane,
        .rg-location-map-shell .leaflet-tile-pane,
        .rg-location-map-shell .leaflet-overlay-pane,
        .rg-location-map-shell .leaflet-shadow-pane,
        .rg-location-map-shell .leaflet-marker-pane,
        .rg-location-map-shell .leaflet-tooltip-pane,
        .rg-location-map-shell .leaflet-popup-pane,
        .rg-location-map-shell .leaflet-top,
        .rg-location-map-shell .leaflet-bottom,
        .rg-location-map-shell .leaflet-control {
          position: absolute !important;
        }
        .rg-location-map-shell .leaflet-tile-container img,
        .rg-location-map-shell .leaflet-tile {
          position: absolute !important;
          max-width: none !important;
        }
        .rg-place-autocomplete-host {
          min-height: 2.75rem;
          width: 100%;
        }
        .rg-place-autocomplete-host rg-place-autocomplete,
        .rg-place-autocomplete-host .rg-address-autocomplete-widget {
          width: 100%;
          display: block;
          --gmp-mat-color-surface: #1e293b;
          --gmp-mat-color-on-surface: #f8fafc;
          color-scheme: dark;
        }
      `}</style>

      {placesOn && (
        <div className="space-y-2">
          <label
            id="job-site-address-label"
            className="block text-sm font-bold text-emerald-300"
          >
            Optional: search address (Places)
          </label>
          <AddressAutocomplete
            disabled={disabled}
            resetKey={resetKey}
            onSelection={handlePlacesSelection}
          />
          <p className="text-xs text-gray-400">
            Or type street, city, state, and ZIP below — the map pin updates automatically.
          </p>
        </div>
      )}

      <div className="bg-slate-700/50 p-4 rounded-lg border border-purple-500/30 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-bold text-white flex items-center gap-2">
            <MapPin className="w-4 h-4 text-emerald-400" />
            Site address
          </p>
          {locationConfirmed && pinReady ? (
            <p className="flex items-center gap-1.5 text-xs text-emerald-300 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              Pin locked (optional)
            </p>
          ) : pinReady ? (
            <p className="text-xs text-gray-400 font-medium">Pin placed — editable</p>
          ) : null}
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          {locationConfirmed ? (
            <button
              type="button"
              onClick={unlockPin}
              disabled={disabled}
              className="flex-1 px-3 py-2.5 min-h-[44px] rounded-lg border border-amber-500/50 bg-amber-500/10 hover:bg-amber-500/20 text-amber-100 text-sm font-bold disabled:opacity-50"
            >
              Unlock pin
            </button>
          ) : pinReady ? (
            <button
              type="button"
              onClick={lockPin}
              disabled={disabled}
              className="flex-1 px-3 py-2.5 min-h-[44px] rounded-lg border border-slate-500 bg-slate-900/60 hover:bg-slate-800 text-white text-sm font-semibold disabled:opacity-50"
            >
              Lock pin (optional)
            </button>
          ) : null}
          <button
            type="button"
            onClick={clearSite}
            disabled={disabled}
            className="flex-1 px-3 py-2.5 min-h-[44px] rounded-lg border border-slate-500 bg-slate-900/60 hover:bg-slate-800 text-white text-sm font-semibold disabled:opacity-50"
          >
            Clear site
          </button>
        </div>
        {pinReady && (
          <p className="text-xs text-gray-400">
            Coordinates: {lat!.toFixed(5)}, {lng!.toFixed(5)}
          </p>
        )}
        <div data-rg-site-fields>
          <div>
            <label className="block text-gray-300 text-xs font-semibold mb-1" htmlFor="rg-jobsite-street">
              Street *
            </label>
            <input
              key={`rg-street-${resetKey}`}
              id="rg-jobsite-street"
              type="text"
              name={`rg_jobsite_street_${resetKey}`}
              value={address}
              onChange={onFieldChange(setAddress)}
              onFocus={markSiteFieldFocused}
              onBlur={onSiteFieldBlur}
              disabled={disabled || locationConfirmed}
              readOnly={!siteFieldsUnlocked}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm disabled:opacity-70"
              placeholder=""
              autoComplete="new-password"
              autoCorrect="off"
              spellCheck={false}
              data-lpignore="true"
              data-1p-ignore="true"
              data-form-type="other"
            />
          </div>
          <div className="grid grid-cols-3 gap-2 mt-3">
            <div>
              <label className="block text-gray-300 text-xs font-semibold mb-1" htmlFor="rg-jobsite-city">
                City *
              </label>
              <input
                key={`rg-city-${resetKey}`}
                id="rg-jobsite-city"
                type="text"
                name={`rg_jobsite_city_${resetKey}`}
                value={city}
                onChange={onFieldChange(setCity)}
                onFocus={markSiteFieldFocused}
                onBlur={onSiteFieldBlur}
                disabled={disabled || locationConfirmed}
                readOnly={!siteFieldsUnlocked}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm disabled:opacity-70"
                placeholder=""
                autoComplete="new-password"
                data-lpignore="true"
                data-1p-ignore="true"
                data-form-type="other"
              />
            </div>
            <div>
              <label className="block text-gray-300 text-xs font-semibold mb-1" htmlFor="rg-jobsite-state">
                State *
              </label>
              <input
                key={`rg-state-${resetKey}`}
                id="rg-jobsite-state"
                type="text"
                name={`rg_jobsite_state_${resetKey}`}
                value={state}
                onChange={onFieldChange(setState)}
                onFocus={markSiteFieldFocused}
                onBlur={onSiteFieldBlur}
                disabled={disabled || locationConfirmed}
                readOnly={!siteFieldsUnlocked}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm disabled:opacity-70"
                placeholder=""
                autoComplete="new-password"
                data-lpignore="true"
                data-1p-ignore="true"
                data-form-type="other"
              />
            </div>
            <div>
              <label className="block text-gray-300 text-xs font-semibold mb-1" htmlFor="rg-jobsite-zip">
                ZIP *
              </label>
              <input
                key={`rg-zip-${resetKey}`}
                id="rg-jobsite-zip"
                type="text"
                name={`rg_jobsite_zip_${resetKey}`}
                value={zip}
                onChange={onFieldChange(setZip)}
                onFocus={markSiteFieldFocused}
                onBlur={onSiteFieldBlur}
                disabled={disabled || locationConfirmed}
                readOnly={!siteFieldsUnlocked}
                inputMode="numeric"
                className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm disabled:opacity-70"
                placeholder=""
                autoComplete="new-password"
                data-lpignore="true"
                data-1p-ignore="true"
                data-form-type="other"
              />
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={handleConfirmLocation}
          disabled={disabled || loading || locationConfirmed}
          className="w-full px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold rounded-lg transition shadow-lg shadow-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading
            ? 'Placing pin…'
            : pinReady
              ? 'Update pin from address'
              : 'Find on map'}
        </button>
        {pinReady && !locationConfirmed ? (
          <p className="text-center text-gray-400 text-xs">
            Pin is ready and editable. Lock only if you want to freeze these fields.
          </p>
        ) : null}
        {locationConfirmed ? (
          <p className="text-center text-green-400 font-bold text-sm">
            ✓ Pin locked — Unlock above to edit
          </p>
        ) : null}
      </div>

      <button
        type="button"
        onClick={handleAutoDetect}
        disabled={disabled || loading || collapseMap}
        className="w-full px-4 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-bold rounded-lg transition shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        <Navigation className="w-4 h-4" />
        {loading ? 'Detecting / reading address…' : 'Auto-Detect My Location'}
      </button>

      {error && (
        <div className="flex gap-3 p-4 bg-amber-500/15 border border-amber-500/35 rounded-lg">
          <AlertCircle className="w-5 h-5 text-amber-300 flex-shrink-0 mt-0.5" />
          <p className="text-amber-100 text-sm">{error}</p>
        </div>
      )}

      {collapseMap && locationConfirmed && (
        <div className="text-center text-green-400 font-bold text-sm">
          ✓ Location confirmed — map hidden while results are open
        </div>
      )}

      {showMapUi && (
        <div className="space-y-2 relative" style={{ position: 'relative', zIndex: 0 }}>
          <div
            ref={mapContainer}
            className="rg-location-map-shell w-full h-80 rounded-lg border border-purple-500/30 bg-slate-700"
            style={MAP_SHELL_STYLE}
          />
          <p className="text-gray-400 text-sm text-center">
            Type the site address above to drop the pin — or click the map to nudge it
          </p>
        </div>
      )}
    </div>
  );
}
