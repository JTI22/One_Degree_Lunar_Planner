"""Fetch topocentric Sun and Earth positions from JPL Horizons for every site."""

import time
from pathlib import Path

import pandas as pd
from astroquery.jplhorizons import Horizons

from sites import SITES, PLANNING_WINDOW, REPLAY_WINDOWS

PROJECT_DIR = Path(__file__).resolve().parent
OUT_DIR = PROJECT_DIR / "data" / "horizons"

BODIES = {"sun": "10", "earth": "399"}
MOON_ID = 301
PLANNING_STEP = "1h"
REPLAY_STEP = "10m"


def slug(name):
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def fetch(body_id, site, start, stop, step, retries=3):
    location = {"lon": site["lon"] % 360, "lat": site["lat"], "elevation": 0.0, "body": MOON_ID}
    for attempt in range(1, retries + 1):
        try:
            query = Horizons(id=body_id, location=location,
                             epochs={"start": start, "stop": stop, "step": step})
            eph = query.ephemerides(quantities="4,13", cache=False)
            return pd.DataFrame({
                "time_utc": pd.to_datetime(list(eph["datetime_str"]), format="%Y-%b-%d %H:%M"),
                "az_deg": list(eph["AZ"]),
                "el_deg": list(eph["EL"]),
                "radius_deg": [w / 7200.0 for w in eph["ang_width"]],
            })
        except Exception as err:
            print(f"    attempt {attempt} failed: {err}")
            time.sleep(5 * attempt)
    raise RuntimeError(f"Horizons request failed for {site['name']}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for site in SITES:
        if site["kind"] == "planning":
            start, stop = PLANNING_WINDOW
            step, run = PLANNING_STEP, "plan"
        else:
            start, stop = REPLAY_WINDOWS[site["name"]]
            step, run = REPLAY_STEP, "replay"

        for body, body_id in BODIES.items():
            out = OUT_DIR / f"{slug(site['name'])}_{body}_{run}.csv"
            if out.exists():
                print(f"Skip (already saved): {out.name}")
                continue
            print(f"Fetching {body:5s} for {site['name']} ({start} to {stop}, step {step})")
            df = fetch(body_id, site, start, stop, step)
            df.to_csv(out, index=False)
            print(f"    saved {len(df)} rows -> {out.name}")

    print("\nAll Horizons data saved in", OUT_DIR)


if __name__ == "__main__":
    main()