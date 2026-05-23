import { FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { routesApi } from '../api/routes';
import { MapRouteEditor } from '../components/MapRouteEditor';
import type { RouteDetail, RouteStop } from '../api/types';
import { useAuth } from '../context/AuthContext';

const TAG_OPTIONS = ['scenic', 'twisty', 'family', 'sunset', 'cruise', 'photo'];

export function EditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [route, setRoute] = useState<RouteDetail | null>(null);
  const [stops, setStops] = useState<RouteStop[]>([]);
  const [polyline, setPolyline] = useState<number[][] | null>(null);
  const [title, setTitle] = useState('Untitled route');
  const [description, setDescription] = useState('');
  const [region, setRegion] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [status, setStatus] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    if (id) {
      routesApi.get(Number(id)).then((r) => {
        setRoute(r);
        setTitle(r.title);
        setDescription(r.description ?? '');
        setRegion(r.region ?? '');
        setTags(r.tags);
        setStops(r.stops);
        setPolyline(r.polyline);
      });
    } else {
      routesApi.create({ title: 'Untitled route' }).then((r) => {
        setRoute(r);
        navigate(`/editor/${r.id}`, { replace: true });
      });
    }
  }, [id, user, navigate]);

  if (!user) {
    return (
      <div className="page">
        <p>Please <Link to="/login">sign in</Link> to create routes.</p>
      </div>
    );
  }

  const saveMetadata = async () => {
    if (!route) return;
    setSaving(true);
    try {
      const updated = await routesApi.update(route.id, {
        title,
        description: description || undefined,
        region: region || undefined,
        tags,
        stops: stops.map((s, i) => ({
          sequence: i,
          lat: s.lat,
          lng: s.lng,
          name: s.name,
          note: s.note,
        })),
      });
      setRoute(updated);
      setStops(updated.stops);
      setStatus('Saved');
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const buildRoute = async () => {
    if (!route) return;
    await saveMetadata();
    setSaving(true);
    try {
      const result = await routesApi.build(route.id);
      setPolyline(result.polyline);
      const refreshed = await routesApi.get(route.id);
      setRoute(refreshed);
      setStatus(
        `Route built — ${(result.distance_meters / 1609.34).toFixed(1)} mi, ${Math.round(result.duration_seconds / 60)} min`,
      );
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Build failed');
    } finally {
      setSaving(false);
    }
  };

  const publish = async () => {
    if (!route) return;
    setSaving(true);
    try {
      await saveMetadata();
      await buildRoute();
      const published = await routesApi.publish(route.id);
      setRoute(published);
      setStatus('Published!');
      navigate(`/routes/${published.id}`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Publish failed');
    } finally {
      setSaving(false);
    }
  };

  const addTag = (e: FormEvent) => {
    e.preventDefault();
    const t = tagInput.trim().toLowerCase();
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagInput('');
  };

  const toggleTag = (t: string) => {
    setTags((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  };

  if (!route && id) {
    return <p className="muted page">Loading editor…</p>;
  }

  return (
    <div className="page editor-page">
      <div className="editor-toolbar">
        <input
          className="title-input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Route title"
        />
        <div className="toolbar-actions">
          <button type="button" className="btn btn-secondary" onClick={saveMetadata} disabled={saving}>
            Save
          </button>
          <button type="button" className="btn btn-secondary" onClick={buildRoute} disabled={saving || stops.length < 2}>
            Build route
          </button>
          <button type="button" className="btn btn-primary" onClick={publish} disabled={saving || stops.length < 2}>
            Publish
          </button>
        </div>
      </div>

      {status && <p className="status-bar">{status}</p>}

      <div className="editor-meta">
        <textarea
          placeholder="Describe the drive…"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
        />
        <input
          placeholder="Region (e.g. Blue Ridge, NC)"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
        />
        <div className="tag-picker">
          {TAG_OPTIONS.map((t) => (
            <button
              key={t}
              type="button"
              className={`tag ${tags.includes(t) ? 'selected' : ''}`}
              onClick={() => toggleTag(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <form onSubmit={addTag} className="tag-add">
          <input
            placeholder="Custom tag"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
          />
          <button type="submit" className="btn btn-ghost">
            Add
          </button>
        </form>
      </div>

      <div className="editor-map-wrap">
        <MapRouteEditor stops={stops} polyline={polyline} onStopsChange={setStops} />
      </div>

      <p className="privacy-note">
        Before publishing: avoid placing stops at your home address. Trim sensitive segments after recording (coming soon).
      </p>
    </div>
  );
}
