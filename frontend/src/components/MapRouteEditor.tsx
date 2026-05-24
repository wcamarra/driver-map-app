import { useCallback, useMemo, useState } from 'react';
import { GoogleMap, Marker, Polyline, useJsApiLoader } from '@react-google-maps/api';
import type { RouteStop } from '../api/types';
import { mapsApi } from '../api/routes';

const mapContainerStyle = { width: '100%', height: '100%' };
const defaultCenter = { lat: 35.5951, lng: -82.5515 };

const mapOptions = {
  disableDefaultUI: false,
  zoomControl: true,
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: true,
  gestureHandling: 'greedy' as const,
};

interface MapRouteEditorProps {
  stops: RouteStop[];
  polyline: number[][] | null;
  onStopsChange: (stops: RouteStop[]) => void;
  readOnly?: boolean;
}

export function MapRouteEditor({
  stops,
  polyline,
  onStopsChange,
  readOnly = false,
}: MapRouteEditorProps) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? '';
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: apiKey,
    libraries: ['places'],
  });

  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [placeQuery, setPlaceQuery] = useState('');
  const [placeResults, setPlaceResults] = useState<
    { name: string; lat: number; lng: number; address: string }[]
  >([]);

  const center = useMemo(() => {
    if (stops.length > 0) return { lat: stops[0].lat, lng: stops[0].lng };
    return defaultCenter;
  }, [stops]);

  const path = useMemo(
    () => (polyline ?? []).map(([lat, lng]) => ({ lat, lng })),
    [polyline],
  );

  const onMapClick = useCallback(
    (e: google.maps.MapMouseEvent) => {
      if (readOnly || !e.latLng) return;
      const lat = e.latLng.lat();
      const lng = e.latLng.lng();
      const next: RouteStop[] = [
        ...stops,
        {
          sequence: stops.length,
          lat,
          lng,
          name: `Stop ${stops.length + 1}`,
          note: null,
        },
      ];
      onStopsChange(next);
    },
    [readOnly, stops, onStopsChange],
  );

  const removeStop = (index: number) => {
    const next = stops
      .filter((_, i) => i !== index)
      .map((s, i) => ({ ...s, sequence: i }));
    onStopsChange(next);
  };

  const moveStop = (index: number, dir: -1 | 1) => {
    const j = index + dir;
    if (j < 0 || j >= stops.length) return;
    const next = [...stops];
    [next[index], next[j]] = [next[j], next[index]];
    onStopsChange(next.map((s, i) => ({ ...s, sequence: i })));
  };

  const searchPlaces = async () => {
    if (!placeQuery.trim()) return;
    try {
      const res = await mapsApi.places(
        placeQuery,
        stops[0]?.lat,
        stops[0]?.lng,
      );
      setPlaceResults(
        res.results.map((p) => ({
          name: p.name,
          lat: p.lat,
          lng: p.lng,
          address: p.address,
        })),
      );
    } catch {
      setPlaceResults([]);
    }
  };

  const addPlaceAsStop = (p: { name: string; lat: number; lng: number }) => {
    onStopsChange([
      ...stops,
      {
        sequence: stops.length,
        lat: p.lat,
        lng: p.lng,
        name: p.name,
        note: null,
      },
    ]);
    setPlaceResults([]);
    setPlaceQuery('');
  };

  if (!apiKey) {
    return (
      <div className="map-placeholder">
        <p>Set <code>VITE_GOOGLE_MAPS_API_KEY</code> in your <code>.env</code> to use the map editor.</p>
        <p>You can still manage stops in the list below.</p>
      </div>
    );
  }

  if (loadError) {
    return <div className="map-placeholder error">Failed to load Google Maps</div>;
  }

  if (!isLoaded) {
    return <div className="map-placeholder">Loading map…</div>;
  }

  return (
    <div className="map-editor">
      <div className="map-canvas">
        <GoogleMap
          mapContainerStyle={mapContainerStyle}
          center={center}
          zoom={stops.length ? 11 : 9}
          options={mapOptions}
          onLoad={setMap}
          onClick={onMapClick}
        >
          {stops.map((s, i) => (
            <Marker
              key={`${s.lat}-${s.lng}-${i}`}
              position={{ lat: s.lat, lng: s.lng }}
              label={String(i + 1)}
              draggable={!readOnly}
              onDragEnd={(e) => {
                if (!e.latLng) return;
                const next = stops.map((stop, idx) =>
                  idx === i
                    ? { ...stop, lat: e.latLng!.lat(), lng: e.latLng!.lng() }
                    : stop,
                );
                onStopsChange(next);
              }}
            />
          ))}
          {path.length > 1 && (
            <Polyline path={path} options={{ strokeColor: '#3b82f6', strokeWeight: 5 }} />
          )}
        </GoogleMap>
      </div>

      {!readOnly && (
        <div className="map-sidebar">
          <p className="hint">Tap the map to add stops. Drag markers to adjust.</p>

          <div className="place-search">
            <input
              type="search"
              placeholder="Search places of interest…"
              value={placeQuery}
              onChange={(e) => setPlaceQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && searchPlaces()}
            />
            <button type="button" className="btn btn-secondary" onClick={searchPlaces}>
              Search
            </button>
          </div>
          {placeResults.length > 0 && (
            <ul className="place-results">
              {placeResults.map((p) => (
                <li key={`${p.lat}-${p.lng}`}>
                  <button type="button" onClick={() => addPlaceAsStop(p)}>
                    <strong>{p.name}</strong>
                    <span>{p.address}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          <ol className="stops-list">
            {stops.map((s, i) => (
              <li key={i}>
                <div className="stop-row">
                  <span className="stop-num">{i + 1}</span>
                  <input
                    value={s.name ?? ''}
                    placeholder="Stop name"
                    onChange={(e) => {
                      const next = [...stops];
                      next[i] = { ...s, name: e.target.value };
                      onStopsChange(next);
                    }}
                  />
                </div>
                <div className="stop-actions">
                  <button type="button" disabled={i === 0} onClick={() => moveStop(i, -1)}>
                    ↑
                  </button>
                  <button
                    type="button"
                    disabled={i === stops.length - 1}
                    onClick={() => moveStop(i, 1)}
                  >
                    ↓
                  </button>
                  <button type="button" className="danger" onClick={() => removeStop(i)}>
                    Remove
                  </button>
                </div>
              </li>
            ))}
          </ol>
          {stops.length > 0 && map && (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                const bounds = new google.maps.LatLngBounds();
                stops.forEach((s) => bounds.extend({ lat: s.lat, lng: s.lng }));
                map.fitBounds(bounds, 48);
              }}
            >
              Fit map to stops
            </button>
          )}
        </div>
      )}
    </div>
  );
}
