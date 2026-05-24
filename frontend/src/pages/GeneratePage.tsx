import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { mapsApi, routesApi } from '../api/routes';
import { useAuth } from '../context/AuthContext';

const PROFILES = [
  { id: 'scenic', label: 'Scenic', desc: 'Quieter roads, longer segments' },
  { id: 'twisty', label: 'Twisty', desc: 'More curves and direction changes' },
  { id: 'relaxed', label: 'Relaxed cruise', desc: 'Easy rolling drives' },
] as const;

export function GeneratePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [locationQuery, setLocationQuery] = useState('');
  const [centerLat, setCenterLat] = useState(35.5951);
  const [centerLng, setCenterLng] = useState(-82.5515);
  const [region, setRegion] = useState('');
  const [profile, setProfile] = useState<'scenic' | 'twisty' | 'relaxed'>('scenic');
  const [durationMinutes, setDurationMinutes] = useState(90);
  const [loading, setLoading] = useState(false);
  const [geocoding, setGeocoding] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  if (!user) {
    return (
      <div className="page">
        <p>
          Please <Link to="/login">sign in</Link> to generate routes.
        </p>
      </div>
    );
  }

  const geocodeLocation = async () => {
    if (!locationQuery.trim()) return;
    setGeocoding(true);
    setError('');
    try {
      const res = await mapsApi.geocode(locationQuery.trim());
      if (!res.results.length) {
        setError('No results for that location');
        return;
      }
      const first = res.results[0];
      setCenterLat(first.lat);
      setCenterLng(first.lng);
      if (!region) setRegion(first.formatted_address);
      setStatus(`Centered on ${first.formatted_address}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Geocoding failed');
    } finally {
      setGeocoding(false);
    }
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setStatus('Finding fun roads nearby… this can take 30–60 seconds.');
    try {
      const route = await routesApi.generate({
        center_lat: centerLat,
        center_lng: centerLng,
        profile,
        duration_minutes: durationMinutes,
        region: region || undefined,
      });
      navigate(`/editor/${route.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
      setStatus('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page generate-page">
      <h1>Generate a route</h1>
      <p className="muted">
        Tell us what kind of drive you want. We&apos;ll suggest a path from OpenStreetMap data — then
        you refine it in the editor and snap it to real roads with Build route.
      </p>

      <form onSubmit={onSubmit} className="generate-form">
        <fieldset>
          <legend>Where</legend>
          <div className="inline-field">
            <input
              type="search"
              placeholder="City or area (e.g. Asheville, NC)"
              value={locationQuery}
              onChange={(e) => setLocationQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), geocodeLocation())}
            />
            <button
              type="button"
              className="btn btn-secondary"
              onClick={geocodeLocation}
              disabled={geocoding}
            >
              {geocoding ? 'Searching…' : 'Find'}
            </button>
          </div>
          <div className="coord-row">
            <label>
              Lat
              <input
                type="number"
                step="any"
                value={centerLat}
                onChange={(e) => setCenterLat(Number(e.target.value))}
                required
              />
            </label>
            <label>
              Lng
              <input
                type="number"
                step="any"
                value={centerLng}
                onChange={(e) => setCenterLng(Number(e.target.value))}
                required
              />
            </label>
          </div>
        </fieldset>

        <fieldset>
          <legend>What kind of drive</legend>
          <div className="profile-grid">
            {PROFILES.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`profile-card ${profile === p.id ? 'selected' : ''}`}
                onClick={() => setProfile(p.id)}
              >
                <strong>{p.label}</strong>
                <span>{p.desc}</span>
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend>How long</legend>
          <label>
            Target drive time (minutes)
            <input
              type="range"
              min={30}
              max={240}
              step={15}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
            />
            <span className="range-value">
              {durationMinutes} min (~{Math.round((durationMinutes * 940) / 1609.34)} mi target)
            </span>
          </label>
        </fieldset>

        <label>
          Region label (optional)
          <input value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Shown on route card" />
        </label>

        {status && <p className="status-bar">{status}</p>}
        {error && <p className="error">{error}</p>}

        <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
          {loading ? 'Generating…' : 'Generate route'}
        </button>
      </form>

      <p className="muted fine-print">
        Generation uses OpenStreetMap — first run may be slow (longer drives download a larger area).
        Rural regions work best for 2+ hour targets. Always review the route before driving.
      </p>
    </div>
  );
}
