"""View the LOLA south-pole terrain and mark the IM-2 landing site."""
from pathlib import Path

import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
from pyproj import CRS, Transformer

PROJECT_DIR = Path(__file__).resolve().parent
DEM_DIR = PROJECT_DIR / "data" / "dem"
STEP = 8  # read every 8th pixel so it loads fast

# Find the terrain file: accepts .tif, .TIF, .tiff, .TIFF
tif_files = sorted(p for p in DEM_DIR.glob("*") if p.suffix.lower() in (".tif", ".tiff"))
if not tif_files:
    raise SystemExit(f"No .tif or .tiff file found in {DEM_DIR}")
DEM_PATH = tif_files[0]
print("Using file:", DEM_PATH.name)
print("File size (MB):", round(DEM_PATH.stat().st_size / 1e6, 1))

with rasterio.open(DEM_PATH) as src:
    print("Size (pixels):", src.width, "x", src.height)
    print("Pixel size (m):", src.res)
    print("Bounds (m):", src.bounds)
    print("Coordinate system:", src.crs)

    dem = src.read(
        1,
        out_shape=(src.height // STEP, src.width // STEP),
        resampling=Resampling.average,
        masked=True,
    )
    bounds = src.bounds
    map_crs = CRS.from_user_input(src.crs.to_wkt())

print("Height min / max:", float(dem.min()), "/", float(dem.max()))

# IM-2 landing site (approximate): 84.78 S, 29.13 E
site_x = site_y = None
try:
    to_map = Transformer.from_crs(map_crs.geodetic_crs, map_crs, always_xy=True)
    site_x, site_y = to_map.transform(29.13, -84.78)
    print("IM-2 map position (km):", round(site_x / 1000, 1), round(site_y / 1000, 1))
except Exception as err:
    print("Could not place the IM-2 site:", err)

extent_km = [bounds.left / 1000, bounds.right / 1000,
             bounds.bottom / 1000, bounds.top / 1000]

plt.figure(figsize=(8, 8))
plt.imshow(dem, cmap="terrain", extent=extent_km)
plt.colorbar(label="Height (file units)")
if site_x is not None:
    plt.plot(site_x / 1000, site_y / 1000, "r*", markersize=14,
             label="IM-2 site (approx.)")
    plt.legend()
plt.xlabel("x (km)")
plt.ylabel("y (km)")
plt.title("LOLA terrain, 80°S to the south pole")
plt.show()