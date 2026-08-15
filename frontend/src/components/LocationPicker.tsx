/**
 * LocationPicker — Auto-detect location or pick on map
 * Uses Geolocation API + OpenStreetMap (free, no API key needed)
 *
 * Map is intentionally position:relative (never sticky/fixed) so it stays
 * in document flow while the page scrolls — especially after results open.
 */

import { useState, useEffect, useRef, type CSSProperties } from 'react';
import { MapPin, Navigation, AlertCircle } from 'lucide-react';

interface LocationPickerProps {
  onLocationSelect: (address: string, city: string, state: string, zip: string, lat: number, lng: number) => void;
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
      onLocationSelect(nextAddress, nextCity, nextState, nextZip, 0, 0);
      setLocationConfirmed(true);
    }
    // intentionally only when externalValues identity/content changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    externalValues?.address,
    externalValues?.city,
    externalValues?.state,
    externalValues?.zip,
  ]);

  // After research results open: tear down Leaflet so tiles/panes cannot float while scrolling
  useEffect(() => {
    if (collapseMap) {
      destroyMap();
    }
  }, [collapseMap]);

  useEffect(() => () => destroyMap(), []);

  // Auto-detect current location
  const handleAutoDetect = async () => {
    setLoading(true);
    setError('');

    if (!navigator.geolocation) {
      setError('Geolocation not supported in your browser');
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setLat(latitude);
        setLng(longitude);
        reverseGeocode(latitude, longitude);
        setMapVisible(true);
      },
      () => {
        setError(`Location access denied. Try clicking the map to pick a location.`);
        setMapVisible(true);
        setLoading(false);
      }
    );
  };

  // Reverse geocode coordinates to address
  const reverseGeocode = async (latitude: number, longitude: number) => {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`
      );
      const data = await response.json();

      const addr = data.address;
      setAddress(data.name || addr.road || addr.house_number || `${latitude}, ${longitude}`);
      setCity(addr.city || addr.town || addr.village || '');
      setState(addr.state || '');
      setZip(addr.postcode || '');
      setLoading(false);
    } catch {
      setError('Could not determine address from coordinates');
      setLoading(false);
    }
  };

  // Initialize map (only when visible and not collapsed by results modal)
  useEffect(() => {
    if (collapseMap || !mapVisible || !mapContainer.current || mapRef.current) return;

    const loadLeaflet = async () => {
      const L = (window as any).L;
      if (!L) {
        if (!document.querySelector('link[data-rg-leaflet]')) {
          const cssLink = document.createElement('link');
          cssLink.rel = 'stylesheet';
          cssLink.href = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
          cssLink.setAttribute('data-rg-leaflet', '1');
          document.head.appendChild(cssLink);
        }

        if (!document.querySelector('script[data-rg-leaflet]')) {
          const script = document.createElement('script');
          script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
          script.setAttribute('data-rg-leaflet', '1');
          script.onload = () => {
            initializeMap();
          };
          document.body.appendChild(script);
        } else {
          const existing = document.querySelector('script[data-rg-leaflet]') as HTMLScriptElement;
          if ((window as any).L) initializeMap();
          else existing.addEventListener('load', () => initializeMap(), { once: true });
        }
      } else {
        initializeMap();
      }
    };

    const initializeMap = () => {
      if (!mapContainer.current || mapRef.current) return;
      const L = (window as any).L;
      if (!L) return;
      const initialLat = lat || 38.5;
      const initialLng = lng || -96.5;

      const map = L.map(mapContainer.current, {
        // Prefer non-CSS-transform path where possible to avoid compositor "float" bugs
        preferCanvas: true,
      }).setView([initialLat, initialLng], 13);
      mapRef.current = map;

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
      }).addTo(map);

      if (lat && lng) {
        L.marker([lat, lng], {
          title: 'Selected Location',
        }).addTo(map);
      }

      map.on('click', async (e: any) => {
        const { lat: clickLat, lng: clickLng } = e.latlng;
        setLat(clickLat);
        setLng(clickLng);

        map.eachLayer((layer: any) => {
          if (layer instanceof L.Marker) {
            map.removeLayer(layer);
          }
        });

        L.marker([clickLat, clickLng], {
          title: 'Selected Location',
        }).addTo(map);

        await reverseGeocode(clickLat, clickLng);
      });

      // Ensure size is correct after layout
      setTimeout(() => {
        try {
          map.invalidateSize();
        } catch {
          /* ignore */
        }
      }, 100);
    };

    loadLeaflet();
  }, [mapVisible, lat, lng, collapseMap]);

  const handleConfirmLocation = () => {
    if (!address || !city || !state || !zip || lat === null || lng === null) {
      setError('Please select a valid location with ZIP code');
      return;
    }
    const fullAddress = `${address}, ${city}, ${state} ${zip}`;
    onLocationSelect(fullAddress, city, state, zip, lat, lng);
    setLocationConfirmed(true);
  };

  const showMapUi = mapVisible && !collapseMap;

  return (
    <div className="space-y-4 relative" style={{ position: 'relative', zIndex: 0, transform: 'none' }}>
      {/* Pin Leaflet panes inside the shell — never sticky/fixed to the viewport */}
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
      `}</style>

      {/* Manual Entry Toggle */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setUseManualEntry(false)}
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

      {/* Manual Entry */}
      {useManualEntry && (
        <div className="space-y-4">
          <div>
            <label className="block text-white font-bold mb-2">Street Address *</label>
            <input
              type="text"
              name="rg_street"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
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
                onChange={(e) => setCity(e.target.value)}
                onFocus={unlockFields}
                placeholder="City"
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                readOnly={!fieldsUnlocked}
                data-lpignore="true"
                data-1p-ignore="true"
                data-form-type="other"
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
                onChange={(e) => setState(e.target.value)}
                onFocus={unlockFields}
                placeholder="State"
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                readOnly={!fieldsUnlocked}
                data-lpignore="true"
                data-1p-ignore="true"
                data-form-type="other"
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
                onChange={(e) => setZip(e.target.value)}
                onFocus={unlockFields}
                placeholder="ZIP"
                autoComplete="off"
                inputMode="numeric"
                spellCheck={false}
                readOnly={!fieldsUnlocked}
                data-lpignore="true"
                data-1p-ignore="true"
                data-form-type="other"
                disabled={disabled}
                className="w-full px-4 py-3 bg-slate-700 border border-purple-500/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              if (address && city && state && zip) {
                const fullAddress = `${address}, ${city}, ${state} ${zip}`;
                onLocationSelect(fullAddress, city, state, zip, 0, 0);
                setLocationConfirmed(true);
              }
            }}
            disabled={disabled || !address || !city || !state || !zip}
            className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Confirm Address
          </button>
        </div>
      )}

      {/* Map / Auto-Detect */}
      {!useManualEntry && (
        <div className="space-y-4 relative" style={{ position: 'relative', zIndex: 0 }}>
          <button
            type="button"
            onClick={handleAutoDetect}
            disabled={disabled || loading || collapseMap}
            className="w-full px-4 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-bold rounded-lg transition shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Navigation className="w-4 h-4" />
            {loading ? 'Detecting...' : 'Auto-Detect My Location'}
          </button>

          {error && (
            <div className="flex gap-3 p-4 bg-red-500/20 border border-red-500/30 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-sm">{error}</p>
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
              <p className="text-gray-400 text-sm text-center">Click on the map to select your location</p>

              {address && city && state && zip && (
                <>
                  <fieldset className="bg-slate-700/50 p-4 rounded-lg border border-purple-500/30 space-y-2">
                    <legend className="sr-only">Selected Location Details</legend>
                    <div className="text-gray-300">
                      <label className="text-gray-400">Address:</label> {address}
                    </div>
                    <div className="text-gray-300">
                      <label className="text-gray-400">City:</label> {city}
                    </div>
                    <div className="text-gray-300">
                      <label className="text-gray-400">State:</label> {state}
                    </div>
                    <div className="text-gray-300">
                      <label className="text-gray-400">ZIP:</label> {zip}
                    </div>
                    {lat && lng && (
                      <div className="text-gray-400 text-xs">
                        Coordinates: {lat.toFixed(4)}, {lng.toFixed(4)}
                      </div>
                    )}
                  </fieldset>

                  {!locationConfirmed && (
                    <button
                      type="button"
                      onClick={handleConfirmLocation}
                      disabled={disabled}
                      className="w-full px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold rounded-lg transition shadow-lg shadow-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Confirm This Location
                    </button>
                  )}

                  {locationConfirmed && (
                    <div className="text-center text-green-400 font-bold">
                      ✓ Location confirmed
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
