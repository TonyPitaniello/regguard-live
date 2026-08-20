/**
 * LocationPicker — Auto-detect location or pick on map
 * Reverse geocode goes through Reg Guard API (Google) — not browser Nominatim (CORS/hangs).
 * Confirm This Location always appears once a pin is set, with editable fields for missing ZIP/city.
 */

import { useState, useEffect, useRef, type CSSProperties } from 'react';
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
  const [mapVisible, setMapVisible] = useState(false);
  const [useManualEntry, setUseManualEntry] = useState(true);
  const [locationConfirmed, setLocationConfirmed] = useState(false);
  const [fieldsUnlocked, setFieldsUnlocked] = useState(false);
  const unlockFields = () => setFieldsUnlocked(true);
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const latLngRef = useRef<{ lat: number; lng: number } | null>(null);

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

  // Sync voice-fill / external parent values into local fields
  useEffect(() => {
    if (!externalValues) return;
    const nextAddress = externalValues.address ?? '';
    const nextCity = externalValues.city ?? '';
    const nextState = externalValues.state ?? '';
    const nextZip = externalValues.zip ?? '';
    if (!nextAddress && !nextCity && !nextState && !nextZip) return;
    setUseManualEntry(true);
    setFieldsUnlocked(true);
    if (nextAddress) setAddress(nextAddress);
    if (nextCity) setCity(nextCity);
    if (nextState) setState(nextState);
    if (nextZip) setZip(nextZip);
    if (nextAddress && nextCity && nextState && nextZip) {
      // Voice fill has no pin — parent may still run; do not fake coords
      onLocationSelect(nextAddress, nextCity, nextState, nextZip, 0, 0);
      setLocationConfirmed(false);
    }
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

  useEffect(() => () => destroyMap(), []);

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
        setFieldsUnlocked(true);
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
      setFieldsUnlocked(true);

      if (nextStreet && nextCity && nextState && nextZip.length === 5) {
        // Auto-confirm happy path — no extra green-button tap
        onLocationSelect(nextStreet, nextCity, nextState, nextZip, latitude, longitude);
        setLocationConfirmed(true);
        setError('');
      } else {
        setError(
          'Pin set — complete any missing city / state / ZIP below, then tap Confirm This Location.'
        );
      }
    } catch {
      setError(
        'Address lookup timed out — keep the pin, fill city / state / ZIP below, then confirm.'
      );
      setFieldsUnlocked(true);
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
    setUseManualEntry(false);
    placeMarker(latitude, longitude);
    await reverseGeocode(latitude, longitude);
  };

  const handleAutoDetect = () => {
    setLoading(true);
    setError('');
    setLocationConfirmed(false);

    if (!navigator.geolocation) {
      setError('Geolocation not supported — click the map or use Manual Entry.');
      setMapVisible(true);
      setUseManualEntry(false);
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        void applyPin(position.coords.latitude, position.coords.longitude);
      },
      () => {
        setError('Location access denied — click the map to pick a site, or use Manual Entry.');
        setMapVisible(true);
        setUseManualEntry(false);
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
      const initialLat = seed?.lat ?? lat ?? 27.99;
      const initialLng = seed?.lng ?? lng ?? -82.53;

      const map = L.map(mapContainer.current, { preferCanvas: true }).setView(
        [initialLat, initialLng],
        seed || (lat && lng) ? 13 : 6
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
      setFieldsUnlocked(true);
      return;
    }
    if (lat === null || lng === null) {
      setError('Search an address, use Auto-Detect, or click the map to set a pin first.');
      return;
    }
    // Street only — parent + backend compose place parts (avoids duplicated address)
    onLocationSelect(address.trim(), city.trim(), state.trim(), zip5, lat, lng);
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
    setFieldsUnlocked(true);
    setUseManualEntry(false);

    const latitude = sel.lat;
    const longitude = sel.lng;
    if (
      latitude != null &&
      longitude != null &&
      Number.isFinite(latitude) &&
      Number.isFinite(longitude) &&
      !(Math.abs(latitude) < 1e-6 && Math.abs(longitude) < 1e-6)
    ) {
      latLngRef.current = { lat: latitude, lng: longitude };
      setLat(latitude);
      setLng(longitude);
      setMapVisible(true);
      placeMarker(latitude, longitude);
      if (street && nextCity && nextState && nextZip.length === 5) {
        onLocationSelect(street, nextCity, nextState, nextZip, latitude, longitude);
        setLocationConfirmed(true);
        setError('');
        return;
      }
    }
    setLocationConfirmed(false);
    setError('Address found — confirm city / state / ZIP, then tap Confirm This Location.');
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
            Search address (Places) — pin + confirm in one step
          </label>
          <AddressAutocomplete disabled={disabled} onSelection={handlePlacesSelection} />
          <p className="text-xs text-gray-400">
            Pick a Google suggestion to lock street, city, ZIP, and map coordinates. Use Map only
            if you need to nudge the pin.
          </p>
          {locationConfirmed && pinReady && (
            <p className="flex items-center gap-2 text-sm text-emerald-300 font-semibold">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              Pin locked — ready to run research
            </p>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => {
            setUseManualEntry(false);
            setMapVisible(true);
          }}
          disabled={disabled}
          className={`flex-1 px-4 py-2 rounded-lg font-bold transition ${
            !useManualEntry
              ? 'bg-purple-600 text-white'
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          <MapPin className="w-4 h-4 inline mr-2" />
          Map/Auto-Detect
        </button>
        <button
          type="button"
          onClick={() => setUseManualEntry(true)}
          disabled={disabled}
          className={`flex-1 px-4 py-2 rounded-lg font-bold transition ${
            useManualEntry
              ? 'bg-purple-600 text-white'
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Manual Entry
        </button>
      </div>

      {useManualEntry && (
        <div className="space-y-4">
          <div>
            <label className="block text-white font-bold mb-2">Street Address *</label>
            <input
              type="text"
              name="rg_street"
              value={address}
              onChange={(e) => {
                setAddress(e.target.value);
                setLocationConfirmed(false);
              }}
              onFocus={unlockFields}
              placeholder="Street address"
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
              readOnly={!fieldsUnlocked}
              data-lpignore="true"
              data-1p-ignore="true"
              data-form-type="other"
              disabled={disabled}
              className="w-full px-4 py-3 bg-slate-700 border border-purple-500/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-white font-bold mb-2">City *</label>
              <input
                type="text"
                name="rg_city"
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setLocationConfirmed(false);
                }}
                onFocus={unlockFields}
                placeholder="City"
                autoComplete="off"
                readOnly={!fieldsUnlocked}
                data-lpignore="true"
                data-1p-ignore="true"
                disabled={disabled}
                className="w-full px-4 py-3 bg-slate-700 border border-purple-500/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
              />
            </div>
            <div>
              <label className="block text-white font-bold mb-2">State *</label>
              <input
                type="text"
                name="rg_state"
                value={state}
                onChange={(e) => {
                  setState(e.target.value);
                  setLocationConfirmed(false);
                }}
                onFocus={unlockFields}
                placeholder="State"
                autoComplete="off"
                readOnly={!fieldsUnlocked}
                data-lpignore="true"
                data-1p-ignore="true"
                disabled={disabled}
                className="w-full px-4 py-3 bg-slate-700 border border-purple-500/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
              />
            </div>
            <div>
              <label className="block text-white font-bold mb-2">ZIP *</label>
              <input
                type="text"
                name="rg_zip"
                value={zip}
                onChange={(e) => {
                  setZip(e.target.value);
                  setLocationConfirmed(false);
                }}
                onFocus={unlockFields}
                placeholder="ZIP"
                autoComplete="off"
                inputMode="numeric"
                readOnly={!fieldsUnlocked}
                data-lpignore="true"
                data-1p-ignore="true"
                disabled={disabled}
                className="w-full px-4 py-3 bg-slate-700 border border-purple-500/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              const zip5 = zip.replace(/\D/g, '').slice(0, 5);
              if (address && city && state && zip5.length === 5) {
                const hasPin =
                  lat != null &&
                  lng != null &&
                  !(Math.abs(lat) < 1e-6 && Math.abs(lng) < 1e-6);
                onLocationSelect(
                  address.trim(),
                  city,
                  state,
                  zip5,
                  hasPin ? lat! : 0,
                  hasPin ? lng! : 0
                );
                setLocationConfirmed(hasPin);
                setError(
                  hasPin
                    ? ''
                    : 'Address saved — add a map pin (Places search or Map) for flood/wetlands GIS.'
                );
              }
            }}
            disabled={disabled || !address || !city || !state || zip.replace(/\D/g, '').length < 5}
            className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Confirm Address
          </button>
        </div>
      )}

      {!useManualEntry && (
        <div className="space-y-4 relative" style={{ position: 'relative', zIndex: 0 }}>
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
            <div className="space-y-4 relative" style={{ position: 'relative', zIndex: 0 }}>
              <div
                ref={mapContainer}
                className="rg-location-map-shell w-full h-80 rounded-lg border border-purple-500/30 bg-slate-700"
                style={MAP_SHELL_STYLE}
              />
              <p className="text-gray-400 text-sm text-center">
                Click the map to drop a pin — then confirm below
              </p>

              {/* Always show confirm panel once a pin exists (even if geocode incomplete) */}
              {pinReady && (
                <div className="bg-slate-700/50 p-4 rounded-lg border border-purple-500/30 space-y-3">
                  <p className="text-sm font-bold text-white">Selected pin</p>
                  <p className="text-xs text-gray-400">
                    Coordinates: {lat!.toFixed(5)}, {lng!.toFixed(5)}
                  </p>
                  <div>
                    <label className="block text-gray-300 text-xs font-semibold mb-1">Street *</label>
                    <input
                      type="text"
                      value={address}
                      onChange={(e) => {
                        setAddress(e.target.value);
                        setLocationConfirmed(false);
                      }}
                      onFocus={unlockFields}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm"
                      placeholder="Street or place name"
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="block text-gray-300 text-xs font-semibold mb-1">City *</label>
                      <input
                        type="text"
                        value={city}
                        onChange={(e) => {
                          setCity(e.target.value);
                          setLocationConfirmed(false);
                        }}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-300 text-xs font-semibold mb-1">State *</label>
                      <input
                        type="text"
                        value={state}
                        onChange={(e) => {
                          setState(e.target.value);
                          setLocationConfirmed(false);
                        }}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm"
                        placeholder="FL"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-300 text-xs font-semibold mb-1">ZIP *</label>
                      <input
                        type="text"
                        value={zip}
                        onChange={(e) => {
                          setZip(e.target.value);
                          setLocationConfirmed(false);
                        }}
                        inputMode="numeric"
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm"
                        placeholder="34201"
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
                      Confirm This Location
                    </button>
                  ) : (
                    <div className="text-center text-green-400 font-bold">✓ Location confirmed</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
