"""Terrain horizon masks: the highest terrain elevation angle in every azimuth around each site."""

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window, from_bounds
from scipy.ndimage import map_coordinates

from sites import SITES

PROJECT_DIR = Path(__file__).resolve().parent
DEM_DIR = PROJECT_DIR / "data" / "dem"
OUT_DIR = PROJECT_DIR / "data" / "masks"

R_MOON = 1737400.0
OBSERVER_HEIGHT = 2.0
MAX_RANGE = 150000.0
AZ_STEP = 0.5
DEM_FILES = {"dem80": "LDEM_80S_80MPP_ADJ", "dem240": "LDEM_60S_240MPP_ADJ"}


def slug(name):
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def find_dem(key):
    matches = [p for p in DEM_DIR.glob(DEM_FILES[key] + ".*") if p.suffix.lower() in (".tif", ".tiff")]
    if not matches:
        raise FileNotFoundError(f"{DEM_FILES[key]} not found in {DEM_DIR}")
    return matches[0]


def elevation_angle(h_point, h_site, distance):
    """Exact apparent elevation (deg) of a terrain point seen from the site on a spherical Moon."""
    delta = distance / R_MOON
    up = (R_MOON + h_point) * np.cos(delta) - (R_MOON + h_site + OBSERVER_HEIGHT)
    out = (R_MOON + h_point) * np.sin(delta)
    return np.degrees(np.arctan2(up, out))


def flat_horizon():
    """Horizon of a perfectly smooth Moon seen from OBSERVER_HEIGHT (deg)."""
    return -np.degrees(np.arccos(R_MOON / (R_MOON + OBSERVER_HEIGHT)))


def local_frame(to_map, lon, lat):
    """Map position, unit north/east vectors and map scale factor at the site."""
    x, y = to_map.transform(lon, lat)
    d = 1e-4
    xn, yn = to_map.transform(lon, lat + d)
    xe, ye = to_map.transform(lon + d, lat)
    north = np.array([xn - x, yn - y])
    east = np.array([xe - x, ye - y])
    true_north = R_MOON * np.radians(d)
    scale = np.linalg.norm(north) / true_north
    return x, y, north / np.linalg.norm(north), east / np.linalg.norm(east), scale


def compute_mask(dem_path, lat, lon):
    with rasterio.open(dem_path) as src:
        map_crs = CRS.from_user_input(src.crs.to_wkt())
        to_map = Transformer.from_crs(map_crs.geodetic_crs, map_crs, always_xy=True)
        x0, y0, north, east, scale = local_frame(to_map, lon, lat)

        pixel = abs(src.transform.a)
        half = MAX_RANGE * scale + 4 * pixel
        window = from_bounds(x0 - half, y0 - half, x0 + half, y0 + half, transform=src.transform)
        window = window.round_offsets().round_lengths().intersection(Window(0, 0, src.width, src.height))
        dem = src.read(1, window=window, masked=True).astype("float64").filled(np.nan)
        transform = src.window_transform(window)

    def sample(xs, ys):
        cols = (np.asarray(xs) - transform.c) / transform.a - 0.5
        rows = (np.asarray(ys) - transform.f) / transform.e - 0.5
        return map_coordinates(dem, [rows, cols], order=1, mode="constant", cval=np.nan)

    h_site = float(sample(np.array([x0]), np.array([y0]))[0])
    if np.isnan(h_site):
        raise ValueError("Site lies outside valid DEM coverage")

    distances = np.arange(pixel, MAX_RANGE + pixel, pixel)
    azimuths = np.arange(0.0, 360.0, AZ_STEP)
    horizon = np.empty_like(azimuths)
    reach = np.empty_like(azimuths)

    for i, az in enumerate(np.radians(azimuths)):
        direction = np.cos(az) * north + np.sin(az) * east
        xs = x0 + direction[0] * distances * scale
        ys = y0 + direction[1] * distances * scale
        heights = sample(xs, ys)
        valid = ~np.isnan(heights)
        angles = elevation_angle(heights[valid], h_site, distances[valid])
        horizon[i] = angles.max() if angles.size else np.nan
        reach[i] = distances[valid].max() / 1000.0 if valid.any() else 0.0

    return pd.DataFrame({"az_deg": azimuths, "horizon_deg": horizon, "reach_km": reach}), h_site


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for site in SITES:
        out = OUT_DIR / f"{slug(site['name'])}.csv"
        if site["map"] == "flat":
            azimuths = np.arange(0.0, 360.0, AZ_STEP)
            mask = pd.DataFrame({"az_deg": azimuths, "horizon_deg": flat_horizon(), "reach_km": np.nan})
            mask.to_csv(out, index=False)
            print(f"{site['name']:18s} flat horizon {flat_horizon():.3f} deg -> {out.name}")
            continue

        mask, h_site = compute_mask(find_dem(site["map"]), site["lat"], site["lon"])
        mask.to_csv(out, index=False)
        short = (mask["reach_km"] < MAX_RANGE / 1000.0 - 1).sum()
        print(f"{site['name']:18s} ground {h_site:8.1f} m | horizon {mask['horizon_deg'].min():6.2f} "
              f"to {mask['horizon_deg'].max():5.2f} deg | short rays {short:3d}/{len(mask)} -> {out.name}")

    print("\nAll horizon masks saved in", OUT_DIR)


if __name__ == "__main__":
    main()