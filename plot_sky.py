"""Sky plots: terrain horizon with the Sun and Earth paths for every site."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from sites import SITES

PROJECT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_DIR / "data" / "results"
MASK_DIR = PROJECT_DIR / "data" / "masks"
OUT_DIR = PROJECT_DIR / "data" / "figures"


def slug(name):
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def plot_site(site):
    name = slug(site["name"])
    run = "plan" if site["kind"] == "planning" else "replay"
    mask = pd.read_csv(MASK_DIR / f"{name}.csv")
    timeline = pd.read_csv(RESULTS_DIR / f"{name}_{run}_timeline.csv")

    fig, ax = plt.subplots(figsize=(11, 4.5))
    floor = min(mask["horizon_deg"].min(), timeline["sun_el"].min(), timeline["earth_el"].min()) - 1
    ax.fill_between(mask["az_deg"], floor, mask["horizon_deg"], color="#8c7b6b", alpha=0.85, label="Terrain horizon")
    ax.scatter(timeline["sun_az"], timeline["sun_el"], s=4, color="#f2a900", label="Sun path")
    ax.scatter(timeline["earth_az"], timeline["earth_el"], s=4, color="#2f7ed8", label="Earth path")
    ax.set_xlim(0, 360)
    ax.set_ylim(floor, None)
    ax.set_xticks(range(0, 361, 45), ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"])
    ax.set_xlabel("Azimuth (direction)")
    ax.set_ylabel("Elevation (deg)")
    ax.set_title(f"{site['name']} ({site['lat']:.2f}, {site['lon']:.2f}) - local sky")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", markerscale=4)
    fig.tight_layout()
    out = OUT_DIR / f"{name}_sky.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)

    earth_az = timeline["earth_az"]
    print(f"{site['name']:18s} Earth az {earth_az.min():6.1f}-{earth_az.max():6.1f} | "
          f"Earth el {timeline['earth_el'].min():6.2f} to {timeline['earth_el'].max():6.2f} | "
          f"terrain there {timeline['earth_horizon'].min():6.2f} to {timeline['earth_horizon'].max():6.2f} -> {out.name}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for site in SITES:
        plot_site(site)
    print("\nSky plots saved in", OUT_DIR)


if __name__ == "__main__":
    main()