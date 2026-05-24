import { Link } from 'react-router-dom';
import type { RouteFeedItem } from '../api/types';

function formatDistance(meters: number | null) {
  if (meters == null) return '—';
  const miles = meters / 1609.34;
  return miles >= 10 ? `${Math.round(miles)} mi` : `${miles.toFixed(1)} mi`;
}

function formatDuration(seconds: number | null) {
  if (seconds == null) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m} min`;
}

export function RouteCard({ route }: { route: RouteFeedItem }) {
  return (
    <Link to={`/routes/${route.id}`} className="route-card">
      <div className="route-card-header">
        <h3>{route.title}</h3>
        {route.avg_rating != null && (
          <span className="rating-badge">★ {route.avg_rating.toFixed(1)}</span>
        )}
      </div>
      {route.description && <p className="route-card-desc">{route.description}</p>}
      <div className="route-card-meta">
        <span>@{route.owner_username}</span>
        {route.region && <span>{route.region}</span>}
        <span>{formatDistance(route.distance_meters)}</span>
        <span>{formatDuration(route.duration_seconds)}</span>
      </div>
      {route.tags.length > 0 && (
        <div className="tag-row">
          {route.tags.map((t) => (
            <span key={t} className="tag">
              {t}
            </span>
          ))}
        </div>
      )}
      <div className="route-card-stats">
        <span>{route.rating_count} ratings</span>
        <span>{route.comment_count} comments</span>
        <span>{route.save_count} saves</span>
      </div>
    </Link>
  );
}
