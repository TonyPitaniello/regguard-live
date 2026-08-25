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
}

const MAP_SHELL_STYLE: CSSProperties = {
  position: 'relative',
  zIndex: 0,
  overflow: 'hidden',
  isolation: 'isolate',
  contain: 'layout paint',
  transform: 'none',
  WebkitTransform: 'none',
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
  const [locationConfirmed, setLocationConfirmed] = useState(false);
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const latLngRef = useRef<{ lat: number; lng: number } | null>(null);
  /** Last query we already resolved (forward / reverse / places) — avoids geocode loops. */
  const settledQueryRef = useRef('');
  const forwardAbortRef = useRef<AbortController | null>(null);

  const destroyMap = () => {
    if (mapRef.current) {
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
    settledQueryRef.current = ''; // allow forward geocode
    if (nextAddress) setAddress(nextAddress);
    if (nextCity) setCity(nextCity);
    if (nextState) setState(nextState);
    if (nextZip) setZip(nextZip);
    setMapVisible(true);
    setLocationConfirmed(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    externalValues?.address,
    externalValues?.city,
    externalValues?.state,
    externalValues?.zip,
  ]);

  useEffect(() => {
    if (collapseMap) destroyMap();
  }, [collapseMap]);

  useEffect(() => () => {
    destroyMap();
    forwardAbortRef.current?.abort();
  }, []);

  const placeMarker = (latitude: number, longitude: number) => {
    const L = (window as any).L;
    const map = mapRef.current;
    if (!L || !map) return;
    if (markerRef.current) {
      try {
        map.removeLayer(markerRef.current);
      } catch {
        /* ignore */
      }
    }
    markerRef.current = L.marker([latitude, longitude], { title: 'Selected Location' }).addTo(map);
    try {
      map.setView([latitude, longitude], Math.max(map.getZoom(), 13));
    } catch {
      /* ignore */
    }
  };

  const commitPin = (
    latitude: number,
    longitude: number,
    street: string,
    nextCity: string,
    nextState: string,
    nextZip: string,
    *,
    autoConfirm: boolean
  ) => {
    latLngRef.current = { lat: latitude, lng: longitude };
    setLat(latitude);
    setLng(longitude);
    setMapVisible(true);
    placeMarker(latitude, longitude);
    settledQueryRef.current = composeQuery(street, nextCity, nextState, nextZip);
    if (autoConfirm && street && nextCity && nextState && nextZip.length === 5) {
      onLocationSelect(street, nextCity, nextState, nextZip, latitude, longitude);
      setLocationConfirmed(true);
      setError('');
    } else {
      setLocationConfirmed(false);
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
      const nextStreet = (data.street || formatted.split(',')[0] || '').trim();
      const nextCity = (data.city || '').trim();
      const nextState = (data.state || parsed.state || '').trim();
      const nextZip = ((data.zip || parsed.zip || '').match(/\d{5}/) || [''])[0];

      setAddress(nextStreet || formatted || `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`);
      setCity(nextCity);
      setState(nextState);
      setZip(nextZip);

      commitPin(
        latitude,
        longitude,
        nextStreet || formatted,
        nextCity,
        nextState,
        nextZip,
        { autoConfirm: Boolean(nextStreet && nextCity && nextState && nextZip.length === 5) }
      );
      if (!(nextStreet && nextCity && nextState && nextZip.length === 5)) {
        setError(
          'Pin set — complete any missing city / state / ZIP below, then tap Confirm This Location.'
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
    placeMarker(latitude, longitude);
    await reverseGeocode(latitude, longitude);
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
      const res = await fetch(`${backendUrl('/geocode-address')}?${params}`, {
        cache: 'no-store',
        signal: controller.signal,
      });
      if (!res.ok) {
        let detail = 'Could not place that address on the map — check spelling or click the map.';
        try {
          const body = await res.json();
          if (typeof body?.detail === 'string' && body.detail.trim()) detail = body.detail;
        } catch {
          /* ignore */
        }
        setError(detail);
        setLocationConfirmed(false);
        return;
      }
      const data = (await res.json()) as {
        street?: string;
        city?: string;
        state?: string;
        zip?: string;
        latitude?: string;
        longitude?: string;
        formatted_address?: string;
      };
      const latitude = Number(data.latitude);
      const longitude = Number(data.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        setError('Could not resolve coordinates for that address.');
        return;
      }
      const resolvedStreet = (data.street || street || data.formatted_address?.split(',')[0] || '').trim();
      const resolvedCity = (data.city || nextCity || '').trim();
      const resolvedState = (data.state || nextState || '').trim();
      const resolvedZip = ((data.zip || nextZip || '').match(/\d{5}/) || [''])[0];

      // Prefer geocoder city/state/ZIP when user left blanks; keep typed street if present
      if (!city.trim() && resolvedCity) setCity(resolvedCity);
      if (!state.trim() && resolvedState) setState(resolvedState);
      if (zip.replace(/\D/g, '').length < 5 && resolvedZip) setZip(resolvedZip);
      if (resolvedStreet && resolvedStreet !== address.trim()) {
        // Only fill street from geocoder when user street was incomplete
        if (street.trim().length < 5) setAddress(resolvedStreet);
      }

      commitPin(
        latitude,
        longitude,
        resolvedStreet || street.trim(),
        resolvedCity || nextCity.trim(),
        resolvedState || nextState.trim(),
        resolvedZip || nextZip.replace(/\D/g, '').slice(0, 5),
        {
          autoConfirm: Boolean(
            (resolvedStreet || street.trim()) &&
              (resolvedCity || nextCity.trim()) &&
              (resolvedState || nextState.trim()) &&
              (resolvedZip || nextZip).replace(/\D/g, '').length === 5
          ),
        }
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

  // Initialize map once when visible
  useEffect(() => {
    if (collapseMap || !mapVisible || !mapContainer.current || mapRef.current) return;

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

      setTimeout(() => {
        try {
          map.invalidateSize();
        } catch {
          /* ignore */
        }
      }, 100);
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
  }, [mapVisible, collapseMap]);

  // Keep marker in sync after map exists
  useEffect(() => {
    if (lat != null && lng != null && mapRef.current) {
      placeMarker(lat, lng);
    }
  }, [lat, lng]);

  const handleConfirmLocation = () => {
    const zip5 = (zip || '').replace(/\D/g, '').slice(0, 5);
    if (!address.trim() || !city.trim() || !state.trim() || zip5.length !== 5) {
      setError('Fill street, city, state, and 5-digit ZIP, then confirm.');
      return;
    }
    if (lat === null || lng === null) {
      void forwardGeocode(address, city, state, zip);
      setError('Placing pin on the map…');
      return;
    }
    onLocationSelect(address.trim(), city.trim(), state.trim(), zip5, lat, lng);
    settledQueryRef.current = composeQuery(address, city, state, zip5);
    setLocationConfirmed(true);
    setError('');
  };

  const handlePlacesSelection = (sel: AddressSelection | null) => {
    if (!sel) {
      setLocationConfirmed(false);
      return;
    }
    const street = (sel.street || sel.formattedAddress.split(',')[0] || '').trim();
    const nextCity = (sel.city || '').trim();
    const nextState = (sel.state || '').trim();
    const nextZip = (sel.zip || '').replace(/\D/g, '').slice(0, 5);
    setAddress(street);
    if (nextCity) setCity(nextCity);
    if (nextState) setState(nextState);
    if (nextZip) setZip(nextZip);

    const latitude = sel.lat;
    const longitude = sel.lng;
    if (
      latitude != null &&
      longitude != null &&
      Number.isFinite(latitude) &&
      Number.isFinite(longitude) &&
      !(Math.abs(latitude) < 1e-6 && Math.abs(longitude) < 1e-6)
    ) {
      commitPin(latitude, longitude, street, nextCity, nextState, nextZip, {
        autoConfirm: Boolean(street && nextCity && nextState && nextZip.length === 5),
      });
      if (!(street && nextCity && nextState && nextZip.length === 5)) {
        setError('Address found — confirm city / state / ZIP, then tap Confirm This Location.');
      }
      return;
    }
    settledQueryRef.current = '';
    setLocationConfirmed(false);
    setError('Address found — complete fields so we can place the pin.');
  };

  const onFieldChange = (setter: (v: string) => void) => (e: ChangeEvent<HTMLInputElement>) => {
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
          <AddressAutocomplete disabled={disabled} onSelection={handlePlacesSelection} />
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
          {locationConfirmed && pinReady && (
            <p className="flex items-center gap-1.5 text-xs text-emerald-300 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              Pin locked
            </p>
          )}
        </div>
        {pinReady && (
          <p className="text-xs text-gray-400">
            Coordinates: {lat!.toFixed(5)}, {lng!.toFixed(5)}
          </p>
        )}
        <div>
          <label className="block text-gray-300 text-xs font-semibold mb-1">Street *</label>
          <input
            type="text"
            value={address}
            onChange={onFieldChange(setAddress)}
            disabled={disabled}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm"
            placeholder="100 W Avenue F"
            autoComplete="off"
          />
        </div>
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="block text-gray-300 text-xs font-semibold mb-1">City *</label>
            <input
              type="text"
              value={city}
              onChange={onFieldChange(setCity)}
              disabled={disabled}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm"
              placeholder="Midlothian"
              autoComplete="off"
            />
          </div>
          <div>
            <label className="block text-gray-300 text-xs font-semibold mb-1">State *</label>
            <input
              type="text"
              value={state}
              onChange={onFieldChange(setState)}
              disabled={disabled}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm"
              placeholder="TX"
              autoComplete="off"
            />
          </div>
          <div>
            <label className="block text-gray-300 text-xs font-semibold mb-1">ZIP *</label>
            <input
              type="text"
              value={zip}
              onChange={onFieldChange(setZip)}
              disabled={disabled}
              inputMode="numeric"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm"
              placeholder="76065"
              autoComplete="off"
            />
          </div>
        </div>

        {!locationConfirmed ? (
          <button
            type="button"
            onClick={handleConfirmLocation}
            disabled={disabled || loading}
            className="w-full px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold rounded-lg transition shadow-lg shadow-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Placing pin…' : pinReady ? 'Confirm This Location' : 'Find on map & confirm'}
          </button>
        ) : (
          <div className="text-center text-green-400 font-bold text-sm">✓ Location confirmed</div>
        )}
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
