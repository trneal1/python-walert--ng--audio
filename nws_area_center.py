#!/usr/bin/env python3
"""Return the center latitude/longitude for an NWS county or SAME code.

Examples:
  python nws_area_center.py 051109
  python nws_area_center.py VAC109
  python nws_area_center.py VAC109 --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from typing import Any


STATE_BY_FIPS = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
    "60": "AS",
    "66": "GU",
    "69": "MP",
    "72": "PR",
    "78": "VI",
}


def code_to_zone(code: str) -> tuple[str, str]:
    """Return (zone_type, zone_id) from a 6-digit SAME or NWS zone code."""
    normalized = code.strip().upper()
    if re.fullmatch(r"\d{6}", normalized):
        state = STATE_BY_FIPS.get(normalized[1:3])
        if not state:
            raise ValueError(f"unknown SAME state FIPS {normalized[1:3]!r}")
        return "county", f"{state}C{normalized[3:]}"

    if re.fullmatch(r"[A-Z]{2}C\d{3}", normalized):
        return "county", normalized

    if re.fullmatch(r"[A-Z]{2}Z\d{3}", normalized):
        return "forecast", normalized

    raise ValueError("use a 6-digit SAME code like 051109, an NWS county code like VAC109, or a forecast zone like VAZ109")


def fetch_zone(zone_type: str, zone_id: str, user_agent: str, timeout: float) -> dict[str, Any]:
    url = f"https://api.weather.gov/zones/{zone_type}/{zone_id}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/geo+json, application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"NWS API returned HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"NWS API request failed for {url}: {exc.reason}") from exc

    geometry = payload.get("geometry")
    if not geometry:
        raise RuntimeError(f"NWS API returned no geometry for {zone_id}")
    return payload


def exterior_rings(geometry: dict[str, Any]) -> list[list[list[float]]]:
    gtype = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if gtype == "Polygon" and isinstance(coordinates, list):
        return [coordinates[0]]
    if gtype == "MultiPolygon" and isinstance(coordinates, list):
        return [polygon[0] for polygon in coordinates if polygon]
    raise RuntimeError(f"unsupported geometry type {gtype!r}")


def polygon_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    if ring[0] != ring[-1]:
        ring = [*ring, ring[0]]

    area = 0.0
    cx = 0.0
    cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross

    area *= 0.5
    if abs(area) < 1e-12:
        raise RuntimeError("zone geometry has zero polygon area")
    return cx / (6.0 * area), cy / (6.0 * area), abs(area)


def center_and_bounds(geometry: dict[str, Any]) -> tuple[float, float, dict[str, float]]:
    total_area = 0.0
    weighted_lon = 0.0
    weighted_lat = 0.0
    all_lons: list[float] = []
    all_lats: list[float] = []

    for ring in exterior_rings(geometry):
        lon, lat, area = polygon_centroid(ring)
        weighted_lon += lon * area
        weighted_lat += lat * area
        total_area += area
        all_lons.extend(point[0] for point in ring)
        all_lats.extend(point[1] for point in ring)

    return (
        weighted_lat / total_area,
        weighted_lon / total_area,
        {
            "west": min(all_lons),
            "south": min(all_lats),
            "east": max(all_lons),
            "north": max(all_lats),
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find the center latitude/longitude for an NWS county or SAME code.")
    parser.add_argument("code", help="6-digit SAME code, NWS county code, or NWS forecast zone code")
    parser.add_argument("--json", action="store_true", help="print full result as JSON")
    parser.add_argument("--timeout", type=float, default=10.0, help="NWS API timeout in seconds")
    parser.add_argument(
        "--user-agent",
        default="nws-area-center/1.0",
        help="User-Agent header sent to api.weather.gov",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        zone_type, zone_id = code_to_zone(args.code)
        payload = fetch_zone(zone_type, zone_id, args.user_agent, args.timeout)
        center_lat, center_lon, bounds = center_and_bounds(payload["geometry"])
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    properties = payload.get("properties", {})
    result = {
        "input": args.code,
        "zone_id": zone_id,
        "zone_type": zone_type,
        "name": properties.get("name", ""),
        "state": properties.get("state", ""),
        "center_lat": round(center_lat, 6),
        "center_lon": round(center_lon, 6),
        "bounds": bounds,
        "source": f"https://api.weather.gov/zones/{zone_type}/{zone_id}",
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['center_lat']},{result['center_lon']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
