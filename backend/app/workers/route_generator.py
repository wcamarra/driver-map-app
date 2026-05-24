"""
Phase 3 spike: generate candidate driving routes from OpenStreetMap road graphs.

Scores edges by profile (scenic, twisty, relaxed). Not wired to HTTP yet — run via:
  python -m app.workers.route_generator
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from itertools import pairwise

import networkx as nx
import osmnx as ox
from shapely.geometry import LineString


@dataclass
class GenerateRequest:
    center_lat: float
    center_lng: float
    radius_m: int = 0  # 0 = auto from target_distance_m
    profile: str = "twisty"
    target_distance_m: float = 25000
    near_lat: float | None = None
    near_lng: float | None = None


@dataclass
class GeneratedRoute:
    polyline: list[list[float]]
    distance_m: float
    edge_count: int
    target_distance_m: float


def radius_for_target(target_distance_m: float) -> int:
    """Download enough road network for the requested drive length."""
    # ~5:1 ratio: 80 mi target → ~16 mi radius disk of roads
    return int(min(max(8000, target_distance_m / 5), 50000))


def edge_curvature_score(line: LineString) -> float:
    """Higher = more direction changes per km (proxy for 'twisty')."""
    if line.length < 100:
        return 0.0
    coords = list(line.coords)
    if len(coords) < 3:
        return 0.0
    bearings: list[float] = []
    for i in range(1, len(coords) - 1):
        dx1 = coords[i][0] - coords[i - 1][0]
        dy1 = coords[i][1] - coords[i - 1][1]
        dx2 = coords[i + 1][0] - coords[i][0]
        dy2 = coords[i + 1][1] - coords[i][1]
        a1 = math.atan2(dy1, dx1)
        a2 = math.atan2(dy2, dx2)
        bearings.append(abs(a2 - a1))
    return sum(bearings) / max(len(bearings), 1) * 1000


def score_edge(data: dict, profile: str, geometry: LineString | None) -> float:
    highway = data.get("highway", "")
    if isinstance(highway, list):
        highway = highway[0] if highway else ""

    scenic_types = {"secondary", "tertiary", "unclassified", "residential"}
    twisty_types = {
        "primary",
        "secondary",
        "tertiary",
        "unclassified",
        "secondary_link",
        "tertiary_link",
    }

    base = 1.0
    if highway in ("motorway", "motorway_link", "trunk", "trunk_link"):
        return 0.0
    if profile == "scenic" and highway in scenic_types:
        base = 2.0
    elif profile == "twisty" and highway in twisty_types:
        base = 1.5
    elif profile == "relaxed":
        base = 1.2 if highway in scenic_types else 0.8

    curve = edge_curvature_score(geometry) if geometry else 0.0
    length = data.get("length", 100) or 100

    if profile == "twisty":
        return base + curve * 0.5
    if profile == "scenic":
        return base + min(length / 500, 3)
    return base


def _edge_length_m(G: nx.MultiDiGraph, u: int, v: int, key: int, data: dict) -> float:
    """Meters along edge (osmnx 2.x removed ox.add_edge_lengths)."""
    geom = data.get("geometry")
    if geom is not None:
        total = 0.0
        for (x1, y1), (x2, y2) in pairwise(geom.coords):
            total += ox.distance.great_circle(y1, x1, y2, x2)
        return total
    nu, nv = G.nodes[u], G.nodes[v]
    return ox.distance.great_circle(nu["y"], nu["x"], nv["y"], nv["x"])


def add_edge_lengths(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    for u, v, key, data in G.edges(keys=True, data=True):
        data["length"] = _edge_length_m(G, u, v, key, data)
    return G


def _walk_graph(G: nx.MultiDiGraph) -> nx.Graph:
    """Undirected graph for random walks (driving roads are mostly two-way)."""
    H = nx.Graph()
    for u, v, _key, data in G.edges(keys=True, data=True):
        length = float(data.get("length") or 1)
        score = float(data.get("score") or 0)
        geom = data.get("geometry")
        if H.has_edge(u, v):
            if score > H.edges[u, v].get("score", 0):
                H.edges[u, v].update(length=length, score=score, geometry=geom)
        else:
            H.add_edge(u, v, length=length, score=score, geometry=geom)
    return H


def _edge_key(u: int, v: int) -> tuple[int, int]:
    return (min(u, v), max(u, v))


def _node_with_options(H: nx.Graph, visited: set[tuple[int, int]]) -> list[int]:
    options: list[int] = []
    for n in H.nodes:
        for nxt in H.neighbors(n):
            if H.edges[n, nxt].get("score", 0) <= 0:
                continue
            if _edge_key(n, nxt) not in visited:
                options.append(n)
                break
    return options


def sample_stops(polyline: list[list[float]], count: int = 5) -> list[tuple[float, float, str]]:
    """Evenly sample waypoints from a polyline as (lat, lng, name)."""
    if not polyline:
        return []
    if len(polyline) <= count:
        return [(p[0], p[1], f"Stop {i + 1}") for i, p in enumerate(polyline)]
    step = max(1, (len(polyline) - 1) // (count - 1))
    indices = list(range(0, len(polyline), step))[:count]
    if indices[-1] != len(polyline) - 1:
        indices[-1] = len(polyline) - 1
    return [(polyline[i][0], polyline[i][1], f"Stop {j + 1}") for j, i in enumerate(indices)]


def nearest_node(G: nx.MultiDiGraph, lat: float, lng: float) -> int:
    return ox.distance.nearest_nodes(G, X=lng, Y=lat)


def generate_route(req: GenerateRequest) -> GeneratedRoute:
    radius = req.radius_m if req.radius_m > 0 else radius_for_target(req.target_distance_m)

    G = ox.graph_from_point(
        (req.center_lat, req.center_lng),
        dist=radius,
        network_type="drive",
        simplify=True,
    )
    G = add_edge_lengths(G)
    nodes = list(G.nodes())
    if len(nodes) < 10:
        raise ValueError("Not enough roads in area — try a larger radius or different location")

    for _u, _v, _k, data in G.edges(keys=True, data=True):
        data["score"] = score_edge(data, req.profile, data.get("geometry"))

    H = _walk_graph(G)
    walk_nodes = list(H.nodes())
    if len(walk_nodes) < 10:
        raise ValueError("Not enough suitable roads for this profile — try scenic or relaxed")

    if req.near_lat is not None and req.near_lng is not None:
        try:
            start = nearest_node(G, req.near_lat, req.near_lng)
        except Exception:
            start = random.choice(walk_nodes)
    else:
        start = random.choice(walk_nodes)

    target = req.target_distance_m
    max_steps = max(500, int(target / 150))
    path = [start]
    total_dist = 0.0
    current = start
    visited_edges: set[tuple[int, int]] = set()
    stuck_spins = 0
    max_stuck_spins = 40

    while total_dist < target * 0.9 and len(path) < max_steps:
        candidates: list[tuple[int, dict]] = []
        for nxt in H.neighbors(current):
            eid = _edge_key(current, nxt)
            if eid in visited_edges:
                continue
            data = H.edges[current, nxt]
            if data.get("score", 0) <= 0:
                continue
            candidates.append((nxt, data))

        if not candidates:
            # Jump to another node that still has unscored roads
            options = _node_with_options(H, visited_edges)
            if options and stuck_spins < max_stuck_spins:
                current = random.choice(options)
                stuck_spins += 1
                continue
            # Last resort: allow reusing edges to reach long targets in small graphs
            if total_dist < target * 0.4 and stuck_spins < max_stuck_spins * 2:
                visited_edges.clear()
                stuck_spins += 1
                continue
            break

        stuck_spins = 0
        candidates.sort(key=lambda x: x[1].get("score", 0), reverse=True)
        top = candidates[: min(6, len(candidates))]
        nxt, data = random.choice(top)
        visited_edges.add(_edge_key(current, nxt))
        path.append(nxt)
        total_dist += float(data.get("length") or 0)
        current = nxt

    coords: list[tuple[float, float]] = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if H.has_edge(u, v):
            geom = H.edges[u, v].get("geometry")
            if geom:
                for x, y in geom.coords:
                    coords.append((y, x))
                continue
        nu, nv = G.nodes[u], G.nodes[v]
        coords.append((nu["y"], nu["x"]))
        if i == 0 or coords[-1] != (nv["y"], nv["x"]):
            coords.append((nv["y"], nv["x"]))

    polyline = [[lat, lng] for lat, lng in coords]
    return GeneratedRoute(
        polyline=polyline,
        distance_m=total_dist,
        edge_count=len(path) - 1,
        target_distance_m=target,
    )


def main() -> None:
    req = GenerateRequest(
        center_lat=35.5951,
        center_lng=-82.5515,
        profile="twisty",
        target_distance_m=20000,
    )
    print(f"Generating {req.profile} route near ({req.center_lat}, {req.center_lng})…")
    result = generate_route(req)
    print(f"Done: ~{result.distance_m / 1000:.1f} km, {result.edge_count} edges, {len(result.polyline)} points")
    if result.polyline:
        print(f"Start: {result.polyline[0]}, End: {result.polyline[-1]}")


if __name__ == "__main__":
    main()
