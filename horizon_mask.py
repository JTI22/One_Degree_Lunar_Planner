"""Terrain horizon masks: the highest terrain elevation angle in every azimuth around each site."""

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Geod, Transformer
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
DEM_FILES = {
    "dem80": "LDEM_80S_80MPP_ADJ",
    "dem240": "LDEM_60S_240MPP_ADJ",
    "dem64": "LDEM_64",
}
GEOD = Geod(a=R_MOON, b=R_MOON)


def slug(name):
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def find_dem(key):
    for suffix in (".tif", ".tiff", ".lbl"):
        for path in DEM_DIR.glob(DEM_FILES[key] + ".*"):
            if path.suffix.lower() == suffix:
                return path
    raise FileNotFoundError(f"{DEM_FILES[key]} not found in {DEM_DIR}")


def elevation_angle(h_point, h_site, distance):
    """Exact apparent elevation (deg) of a terrain point seen from the site on a spherical Moon."""
    delta = distance / R_MOON
    up = (R_MOON + h_point) * np.cos(delta) - (R_MOON + h_site + OBSERVER_HEIGHT)
    out = (R_MOON + h_point) * np.sin(delta)
    return np.degrees(np.arctan2(up, out))


def flat_horizon():
    """Horizon of a perfectly smooth Moon seen from OBSERVER_HEIGHT (deg)."""
    return -np.degrees(np.arccos(R_MOON / (R_MOON + OBSERVER_HEIGHT)))


def compute_mask(dem_path, lat, lon):
    azimuths = np.arange(0.0, 360.0, AZ_STEP)
    with rasterio.open(dem_path) as src:
        pixel_m = abs(src.res[0]) if src.crs.is_projected else np.radians(abs(src.res[0])) * R_MOON
        distances = np.arange(pixel_m, MAX_RANGE + pixel_m, pixel_m)

        az_grid, d_grid = np.meshgrid(azimuths, distances, indexing="ij")
        ray_lon, ray_lat, _ = GEOD.fwd(np.full(az_grid.size, lon), np.full(az_grid.size, lat),
                                       az_grid.ravel(), d_grid.ravel())

        map_crs = CRS.from_user_input(src.crs.to_wkt())
        to_map = Transformer.from_crs(map_crs.geodetic_crs, map_crs, always_xy=True)
        xs, ys = to_map.transform(np.append(ray_lon, lon), np.append(ray_lat, lat))

        margin = 4 * abs(src.res[0])
        window = from_bounds(xs.min() - margin, ys.min() - margin, xs.max() + margin, ys.max() + margin,
                             transform=src.transform)
        window = window.round_offsets().round_lengths().intersection(Window(0, 0, src.width, src.height))
        raw = src.read(1, window=window, masked=True).astype("float64").filled(np.nan)
        transform = src.window_transform(window)
        scale, offset = src.scales[0], src.offsets[0]

    dem = raw * scale + offset
    if offset > 1.0e6:
        dem -= R_MOON

    cols = (xs - transform.c) / transform.a - 0.5
    rows = (ys - transform.f) / transform.e - 0.5
    heights = map_coordinates(dem, [rows, cols], order=1, mode="constant", cval=np.nan)

    h_site = float(heights[-1])
    if np.isnan(h_site):
        raise ValueError("Site lies outside valid DEM coverage")

    heights = heights[:-1].reshape(az_grid.shape)
    angles = elevation_angle(heights, h_site, d_grid)
    valid = ~np.isnan(heights)
    horizon = np.where(valid.any(axis=1), np.nanmax(np.where(valid, angles, np.nan), axis=1), np.nan)
    reach = np.where(valid, d_grid, 0.0).max(axis=1) / 1000.0
    return pd.DataFrame({"az_deg": azimuths, "horizon_deg": horizon, "reach_km": reach}), h_site, pixel_m


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

        mask, h_site, pixel_m = compute_mask(find_dem(site["map"]), site["lat"], site["lon"])
        mask.to_csv(out, index=False)
        short = (mask["reach_km"] < MAX_RANGE / 1000.0 - 1).sum()
        print(f"{site['name']:18s} {site['map']:6s} {pixel_m:5.0f} m/px | ground {h_site:8.1f} m | horizon "
              f"{mask['horizon_deg'].min():6.2f} to {mask['horizon_deg'].max():5.2f} deg | "
              f"short rays {short:3d}/{len(mask)} -> {out.name}")

    print("\nAll horizon masks saved in", OUT_DIR)


if __name__ == "__main__":
    main()