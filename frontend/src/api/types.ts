export interface User {
  id: number;
  email: string;
  username: string;
  display_name: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RouteStop {
  id?: number;
  sequence: number;
  lat: number;
  lng: number;
  name: string | null;
  note: string | null;
}

export interface RouteDetail {
  id: number;
  title: string;
  description: string | null;
  region: string | null;
  tags: string[];
  visibility: string;
  source: string;
  version: number;
  distance_meters: number | null;
  duration_seconds: number | null;
  owner_id: number;
  owner_username: string;
  stops: RouteStop[];
  polyline: number[][] | null;
  avg_rating: number | null;
  rating_count: number;
  comment_count: number;
  save_count: number;
  user_rating: number | null;
  user_saved: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RouteFeedItem {
  id: number;
  title: string;
  description: string | null;
  region: string | null;
  tags: string[];
  visibility: string;
  source: string;
  distance_meters: number | null;
  duration_seconds: number | null;
  owner_username: string;
  avg_rating: number | null;
  rating_count: number;
  comment_count: number;
  save_count: number;
  published_at: string | null;
  preview_polyline: number[][] | null;
}

export interface RouteBuildResult {
  distance_meters: number;
  duration_seconds: number;
  polyline: number[][];
}

export interface Comment {
  id: number;
  route_id: number;
  user_id: number;
  username: string;
  body: string;
  created_at: string;
}

export interface Rating {
  id: number;
  route_id: number;
  user_id: number;
  username: string;
  stars: number;
  fun: number | null;
  scenery: number | null;
  road_quality: number | null;
  created_at: string;
}

export interface PlaceResult {
  name: string;
  place_id: string;
  address: string;
  lat: number;
  lng: number;
  types: string[];
}
