import { api } from './client';
import type {
  Comment,
  Rating,
  RouteBuildResult,
  RouteDetail,
  RouteFeedItem,
  RouteStop,
  TokenResponse,
  User,
} from './types';

export const authApi = {
  register: (body: { email: string; username: string; password: string; display_name?: string }) =>
    api<TokenResponse>('/api/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    api<TokenResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  me: () => api<User>('/api/auth/me'),
};

export const routesApi = {
  create: (body: { title?: string; description?: string; region?: string; tags?: string[] }) =>
    api<RouteDetail>('/api/routes', { method: 'POST', body: JSON.stringify(body) }),
  feed: (params?: { tag?: string; region?: string; q?: string }) => {
    const q = new URLSearchParams();
    if (params?.tag) q.set('tag', params.tag);
    if (params?.region) q.set('region', params.region);
    if (params?.q) q.set('q', params.q);
    const qs = q.toString();
    return api<RouteFeedItem[]>(`/api/routes/feed${qs ? `?${qs}` : ''}`);
  },
  mine: () => api<RouteFeedItem[]>('/api/routes/mine'),
  get: (id: number) => api<RouteDetail>(`/api/routes/${id}`),
  update: (
    id: number,
    body: {
      title?: string;
      description?: string;
      region?: string;
      tags?: string[];
      visibility?: string;
      stops?: Omit<RouteStop, 'id'>[];
    },
  ) => api<RouteDetail>(`/api/routes/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  build: (id: number) =>
    api<RouteBuildResult>(`/api/routes/${id}/build`, { method: 'POST' }),
  publish: (id: number) =>
    api<RouteDetail>(`/api/routes/${id}/publish`, { method: 'POST' }),
  fork: (id: number) => api<RouteDetail>(`/api/routes/${id}/fork`, { method: 'POST' }),
};

export const socialApi = {
  rate: (routeId: number, body: { stars: number; fun?: number; scenery?: number; road_quality?: number }) =>
    api<Rating>(`/api/routes/${routeId}/ratings`, { method: 'POST', body: JSON.stringify(body) }),
  comments: (routeId: number) => api<Comment[]>(`/api/routes/${routeId}/comments`),
  addComment: (routeId: number, body: string) =>
    api<Comment>(`/api/routes/${routeId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    }),
  save: (routeId: number) =>
    api<{ saved: boolean }>(`/api/routes/${routeId}/save`, { method: 'POST' }),
  unsave: (routeId: number) =>
    api<void>(`/api/routes/${routeId}/save`, { method: 'DELETE' }),
};

export const mapsApi = {
  config: () =>
    api<{
      configured: boolean;
      directions_quota_remaining: number;
      places_quota_remaining: number;
    }>('/api/maps/config'),
  places: (q: string, lat?: number, lng?: number) => {
    const params = new URLSearchParams({ q });
    if (lat != null) params.set('lat', String(lat));
    if (lng != null) params.set('lng', String(lng));
    return api<{ results: import('./types').PlaceResult[] }>(`/api/maps/places?${params}`);
  },
  geocode: (address: string) =>
    api<{ results: { formatted_address: string; lat: number; lng: number }[] }>(
      `/api/maps/geocode?address=${encodeURIComponent(address)}`,
    ),
};
