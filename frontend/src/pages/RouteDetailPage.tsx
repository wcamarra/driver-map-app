import { useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { routesApi, socialApi } from '../api/routes';
import { MapRouteEditor } from '../components/MapRouteEditor';
import type { Comment, RouteDetail } from '../api/types';
import { useAuth } from '../context/AuthContext';

function formatDistance(meters: number | null) {
  if (meters == null) return '—';
  return `${(meters / 1609.34).toFixed(1)} mi`;
}

function formatDuration(seconds: number | null) {
  if (seconds == null) return '—';
  const m = Math.round(seconds / 60);
  const h = Math.floor(m / 60);
  return h > 0 ? `${h}h ${m % 60}m` : `${m} min`;
}

export function RouteDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [route, setRoute] = useState<RouteDetail | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [stars, setStars] = useState(5);
  const [commentText, setCommentText] = useState('');
  const [message, setMessage] = useState('');

  const load = async () => {
    const r = await routesApi.get(Number(id));
    setRoute(r);
    setStars(r.user_rating ?? 5);
    if (r.visibility === 'public') {
      const c = await socialApi.comments(r.id);
      setComments(c);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  const rate = async () => {
    if (!route || !user) return;
    await socialApi.rate(route.id, { stars });
    setMessage('Rating saved');
    load();
  };

  const submitComment = async (e: FormEvent) => {
    e.preventDefault();
    if (!route || !user || !commentText.trim()) return;
    await socialApi.addComment(route.id, commentText.trim());
    setCommentText('');
    load();
  };

  const toggleSave = async () => {
    if (!route || !user) return;
    if (route.user_saved) await socialApi.unsave(route.id);
    else await socialApi.save(route.id);
    load();
  };

  const fork = async () => {
    if (!route || !user) return;
    const copy = await routesApi.fork(route.id);
    window.location.href = `/editor/${copy.id}`;
  };

  if (!route) return <p className="muted page">Loading…</p>;

  return (
    <div className="page route-detail">
      <div className="detail-header">
        <div>
          <h1>{route.title}</h1>
          <p className="muted">
            by @{route.owner_username} · {formatDistance(route.distance_meters)} ·{' '}
            {formatDuration(route.duration_seconds)}
          </p>
          {route.region && <p>{route.region}</p>}
          {route.description && <p>{route.description}</p>}
          <div className="tag-row">
            {route.tags.map((t) => (
              <span key={t} className="tag">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="detail-actions">
          {user && (
            <>
              <button type="button" className="btn btn-secondary" onClick={toggleSave}>
                {route.user_saved ? 'Saved ✓' : 'Save route'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={fork}>
                Copy & edit
              </button>
            </>
          )}
          {user?.id === route.owner_id && (
            <Link to={`/editor/${route.id}`} className="btn btn-primary">
              Edit
            </Link>
          )}
        </div>
      </div>

      <div className="detail-map">
        <MapRouteEditor
          stops={route.stops}
          polyline={route.polyline}
          onStopsChange={() => {}}
          readOnly
        />
      </div>

      {route.visibility === 'public' && (
        <section className="social-section">
          <h2>Community</h2>
          <p>
            ★ {route.avg_rating?.toFixed(1) ?? '—'} ({route.rating_count} ratings) ·{' '}
            {route.comment_count} comments · {route.save_count} saves
          </p>

          {user ? (
            <div className="rate-box">
              <label>
                Your rating
                <select value={stars} onChange={(e) => setStars(Number(e.target.value))}>
                  {[5, 4, 3, 2, 1].map((n) => (
                    <option key={n} value={n}>
                      {n} stars
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="btn btn-secondary" onClick={rate}>
                Submit rating
              </button>
            </div>
          ) : (
            <p>
              <Link to="/login">Sign in</Link> to rate and comment.
            </p>
          )}

          {message && <p className="status-bar">{message}</p>}

          <ul className="comments-list">
            {comments.map((c) => (
              <li key={c.id}>
                <strong>@{c.username}</strong>
                <span>{new Date(c.created_at).toLocaleDateString()}</span>
                <p>{c.body}</p>
              </li>
            ))}
          </ul>

          {user && (
            <form onSubmit={submitComment} className="comment-form">
              <textarea
                placeholder="Share your thoughts on this drive…"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                rows={3}
              />
              <button type="submit" className="btn btn-primary">
                Post comment
              </button>
            </form>
          )}
        </section>
      )}
    </div>
  );
}
