"""Farm layout zoning: multi-zone master layout around the well site.

Method (multi-zone centroid master layout, rotated grid polygonization):
  1. Work in local UTM; find the boundary's principal axis via its minimum
     rotated rectangle and rotate the frame so cuts are axis-aligned.
  2. Allocate area bands (config, by total farm size) and guillotine the
     rotated boundary along the long axis into contiguous strips:
     homestead | orchard | ... production (remainder), with a fixed-width
     roads/service strip.
  3. Carve the well pad (square, configurable side) out of whichever zone
     contains the optimal well point.
  4. Rotate/transform back to WGS84 and emit a GeoJSON FeatureCollection
     with measured per-zone areas (UTM) and target vs actual allocations.

Zone polygons partition the field: disjoint, gapless up to float tolerance.
"""
from __future__ import annotations

import json
import math

import geopandas as gpd
from shapely import affinity
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

from app.config import Settings
from app.core.logging import get_logger
from app.core.spatial import geom_from_geojson, to_utm, utm_epsg

log = get_logger(__name__)


def _principal_angle(boundary_utm: BaseGeometry) -> float:
    rect = boundary_utm.minimum_rotated_rectangle
    coords = list(rect.exterior.coords)
    best_angle, best_len = 0.0, -1.0
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length > best_len:
            best_len = length
            best_angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    return best_angle


def _band_for_area(settings: Settings, area_ha: float):
    for band in settings.zoning.bands:
        if area_ha <= band.max_area_ha:
            return band
    return settings.zoning.bands[-1]


def generate_master_layout(
    boundary_geojson: dict,
    well_point_lonlat: tuple[float, float] | None,
    settings: Settings,
) -> dict:
    boundary = geom_from_geojson(boundary_geojson)
    centroid = boundary.centroid
    epsg = utm_epsg(centroid.x, centroid.y)
    b_utm = to_utm(boundary, epsg)
    area_ha = b_utm.area / 10_000.0

    band = _band_for_area(settings, area_ha)
    allocations = dict(band.allocations)

    angle = _principal_angle(b_utm)
    anchor = b_utm.centroid
    rotated = affinity.rotate(b_utm, -angle, origin=anchor)
    minx, miny, maxx, maxy = rotated.bounds
    width = maxx - minx
    height = maxy - miny

    # Well pad conformal point (rotate well point into the cutting frame)
    well_rot = None
    if well_point_lonlat is not None:
        from shapely.geometry import Point

        w_utm = to_utm(Point(*well_point_lonlat), epsg)
        well_rot = affinity.rotate(w_utm, -angle, origin=anchor)

    # Consume the road allocation as a fixed-width strip (not fractional width)
    road_frac = allocations.pop("roads_service", 0.0)
    road_width = settings.zoning.road_width_m if road_frac > 0 else 0.0

    allocatable_width = max(width - road_width, 1e-6)
    order = ["homestead", "orchard"]  # remainder -> production at the far end
    extras = [k for k in allocations if k not in order and k != "production"]
    order.extend(extras)

    zones: list[tuple[str, BaseGeometry, float]] = []
    x_cursor = minx

    def _cut(x0: float, x1: float) -> BaseGeometry:
        return rotated.intersection(box(x0, miny - 1.0, x1, maxy + 1.0))

    for name in order:
        target = allocations.get(name, 0.0) / (1.0 - road_frac if road_frac < 1.0 else 1.0)
        w = target * allocatable_width
        if w <= 0.5:
            continue
        zones.append((name, _cut(x_cursor, x_cursor + w), target))
        x_cursor += w

    if road_width > 0:
        zones.append(("roads_service", _cut(x_cursor, x_cursor + road_width), road_frac))
        x_cursor += road_width

    zones.append(("production", _cut(x_cursor, maxx + 1.0), max(1.0 - sum(allocations.values()), 0.0)))

    # Carve the well pad out of its host zone
    if well_rot is not None and rotated.contains(well_rot.buffer(0.1)):
        half = settings.zoning.well_pad_side_m / 2.0
        pad = rotated.intersection(
            box(well_rot.x - half, well_rot.y - half, well_rot.x + half, well_rot.y + half)
        )
        if not pad.is_empty and pad.area > 4.0:
            zones = [(n, (g.difference(pad) if g.intersects(pad) else g), t) for n, g, t in zones]
            zones.append(("well_site", pad, settings.zoning.well_pad_side_m**2 / max(b_utm.area, 1.0)))

    from app.core.spatial import from_utm

    records = []
    for name, geom_rot, target in zones:
        geom = affinity.rotate(geom_rot, angle, origin=anchor)  # back to UTM frame
        if geom.is_empty or geom.area < 1.0:
            continue
        actual_ha = geom.area / 10_000.0
        records.append(
            {
                "zone": name,
                "area_ha": round(actual_ha, 3),
                "allocation_target_pct": round(100 * float(target), 2),
                "allocation_actual_pct": round(100 * actual_ha / max(area_ha, 1e-9), 2),
                "geometry": from_utm(geom, epsg),
            }
        )

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
    fc = json.loads(gdf.to_json(drop_id=True))
    fc["metadata"] = {
        "total_area_ha": round(area_ha, 3),
        "band_rule_max_area_ha": band.max_area_ha if band.max_area_ha != float("inf") else None,
        "rotation_degrees": round(angle, 2),
        "well_pad_carved": any(r["zone"] == "well_site" for r in records),
    }
    log.info("zoning: %d zones over %.2f ha", len(records), area_ha)
    return fc
