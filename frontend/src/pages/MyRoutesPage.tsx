import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { routesApi } from '../api/routes';
import { RouteCard } from '../components/RouteCard';
import type { RouteFeedItem } from '../api/types';

export function MyRoutesPage() {
  const [routes, setRoutes] = useState<RouteFeedItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    routesApi.mine().then(setRoutes).finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <div className="page-header">
        <h1>My routes</h1>
        <Link to="/editor" className="btn btn-primary">
          New route
        </Link>
      </div>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : routes.length === 0 ? (
        <p className="muted">You have no routes yet.</p>
      ) : (
        <div className="route-grid">
          {routes.map((r) => (
            <div key={r.id} className="route-card-wrap">
              <RouteCard route={r} />
              {r.visibility === 'draft' && (
                <Link to={`/editor/${r.id}`} className="edit-link">
                  Continue editing →
                </Link>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
