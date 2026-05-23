"""
Phase 3 spike: generate candidate driving routes from OpenStreetMap road graphs.

Scores edges by profile (scenic, twisty, relaxed). Not wired to HTTP yet — run via:
  python -m app.workers.route_generator
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import networkx as nx
import osmnx as ox
from shapely.geometry import LineString


@dataclass
class GenerateRequest:
    center_lat: float
    center_lng: float
    radius_m: int = 8000
    profile: str = "twisty"
    target_distance_m: float = 25000


@dataclass
class GeneratedRoute:
    polyline: list[list[float]]
    distance_m: float
    edge_count: int


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
    twisty_types = {"secondary", "tertiary", "unclassified"}

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


def load_graph(req: GenerateRequest) -> nx.MultiDiGraph:
    G = ox.graph_from_point(
        (req.center_lat, req.center_lng),
        dist=req.radius_m,
        network_type="drive",
        simplify=True,
    )
    G = ox.add_edge_lengths(G)
    G = ox.project_graph(G)
    return G


def generate_route(req: GenerateRequest) -> GeneratedRoute:
    G = load_graph(req)
    nodes = list(G.nodes())
    if len(nodes) < 10:
        raise ValueError("Not enough roads in area — try a larger radius")

    for u, v, k, data in G.edges(keys=True, data=True):
        geom = data.get("geometry")
        data["score"] = score_edge(data, req.profile, geom)

    start = random.choice(nodes)
    path = [start]
    total_dist = 0.0
    current = start
    visited_edges: set[tuple] = set()

    while total_dist < req.target_distance_m * 0.85 and len(path) < 400:
        out_edges = []
        for _, nxt, key, data in G.out_edges(current, keys=True, data=True):
            eid = (current, nxt, key)
            if eid in visited_edges:
                continue
            if data.get("score", 0) <= 0:
                continue
            out_edges.append((nxt, key, data))

        if not out_edges:
            break

        out_edges.sort(key=lambda x: x[2].get("score", 0), reverse=True)
        top = out_edges[: min(5, len(out_edges))]
        nxt, key, data = random.choice(top)
        visited_edges.add((current, nxt, key))
        path.append(nxt)
        total_dist += data.get("length", 0)
        current = nxt

    coords: list[tuple[float, float]] = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            continue
        first_key = list(edge_data.keys())[0]
        geom = edge_data[first_key].get("geometry")
        if geom:
            for x, y in geom.coords:
                coords.append((y, x))
        else:
            nu = G.nodes[u]
            nv = G.nodes[v]
            coords.append((nu["y"], nu["x"]))
            coords.append((nv["y"], nv["x"]))

    polyline = [[lat, lng] for lat, lng in coords]
    return GeneratedRoute(polyline=polyline, distance_m=total_dist, edge_count=len(path) - 1)


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
