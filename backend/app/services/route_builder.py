from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import LineString, mapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.route import Route, RouteStop
from app.services.google_maps import extract_route_from_directions, fetch_directions


def linestring_to_coords(geometry) -> list[list[float]] | None:
    if geometry is None:
        return None
    shape = to_shape(geometry)
    return [[lat, lng] for lng, lat in shape.coords]


def coords_to_linestring(coords: list[list[float]]):
    if len(coords) < 2:
        return None
    line = LineString([(c[1], c[0]) for c in coords])
    return from_shape(line, srid=4326)


async def build_route_geometry(route: Route, db: AsyncSession) -> tuple[list[list[float]], float, int]:
    stops = sorted(route.stops, key=lambda s: s.sequence)
    if len(stops) < 2:
        raise ValueError("At least two stops required to build route")

    waypoints = [(s.lat, s.lng) for s in stops]
    data = await fetch_directions(waypoints)
    polyline, distance_m, duration_s = extract_route_from_directions(data)

    route.geometry = coords_to_linestring(polyline)
    route.distance_meters = distance_m
    route.duration_seconds = duration_s
    await db.flush()

    return polyline, distance_m, duration_s
