import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { routesApi } from '../api/routes';
import { RouteCard } from '../components/RouteCard';
import type { RouteFeedItem } from '../api/types';

export function HomePage() {
  const [routes, setRoutes] = useState<RouteFeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [tag, setTag] = useState('');
  const [region, setRegion] = useState('');
  const [q, setQ] = useState('');

  const load = () => {
    setLoading(true);
    routesApi
      .feed({ tag: tag || undefined, region: region || undefined, q: q || undefined })
      .then(setRoutes)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page">
      <section className="hero">
        <h1>Find your next great drive</h1>
        <p>Scenic backroads, twisty favorites, and day-trip routes shared by driving enthusiasts.</p>
        <div className="hero-actions">
          <Link to="/editor" className="btn btn-primary btn-lg">
            Create a route
          </Link>
          <Link to="/generate" className="btn btn-secondary btn-lg">
            Generate a route
          </Link>
        </div>
      </section>

      <section className="filters">
        <input
          placeholder="Search routes…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <input
          placeholder="Tag (e.g. scenic)"
          value={tag}
          onChange={(e) => setTag(e.target.value)}
        />
        <input
          placeholder="Region"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
        />
        <button type="button" className="btn btn-secondary" onClick={load}>
          Filter
        </button>
      </section>

      {loading ? (
        <p className="muted">Loading routes…</p>
      ) : routes.length === 0 ? (
        <p className="muted">No public routes yet. Be the first to publish one!</p>
      ) : (
        <div className="route-grid">
          {routes.map((r) => (
            <RouteCard key={r.id} route={r} />
          ))}
        </div>
      )}
    </div>
  );
}
