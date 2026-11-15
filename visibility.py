"""Sun and Earth visibility above the terrain horizon: timelines, events and landing-date comparison."""

from pathlib import Path

import numpy as np
import pandas as pd

from sites import SITES

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
HORIZONS_DIR = DATA_DIR / "horizons"
MASK_DIR = DATA_DIR / "masks"
OUT_DIR = DATA_DIR / "results"

PLAN_DAYS = 30


def slug(name):
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def disk_fraction(margin, radius):
    """Visible fraction of a disk whose centre is `margin` deg above a straight horizon."""
    m = np.clip(np.asarray(margin, dtype=float) / radius, -1.0, 1.0)
    hidden = (np.arccos(m) - m * np.sqrt(1.0 - m ** 2)) / np.pi
    return 1.0 - hidden


def horizon_at(mask, azimuth):
    return np.interp(np.asarray(azimuth) % 360.0, mask["az_deg"], mask["horizon_deg"], period=360.0)


def build_timeline(site, run):
    mask = pd.read_csv(MASK_DIR / f"{slug(site['name'])}.csv")
    frames = {}
    for body in ("sun", "earth"):
        eph = pd.read_csv(HORIZONS_DIR / f"{slug(site['name'])}_{body}_{run}.csv", parse_dates=["time_utc"])
        horizon = horizon_at(mask, eph["az_deg"])
        margin = eph["el_deg"] - horizon
        frames[body] = pd.DataFrame({
            f"{body}_az": eph["az_deg"],
            f"{body}_el": eph["el_deg"],
            f"{body}_horizon": horizon,
            f"{body}_margin": margin,
            f"{body}_radius": eph["radius_deg"],
            f"{body}_visible_frac": disk_fraction(margin, eph["radius_deg"]),
        })
    timeline = pd.concat([eph["time_utc"], frames["sun"], frames["earth"]], axis=1)
    timeline["sun_up"] = timeline["sun_visible_frac"] > 0
    timeline["earth_up"] = timeline["earth_visible_frac"] > 0
    timeline["both_up"] = timeline["sun_up"] & timeline["earth_up"]
    return timeline


def find_events(timeline):
    """Interpolated times when the whole Sun or Earth disk sets below / rises above the terrain."""
    names = {"sun": ("sunset", "sunrise"), "earth": ("earthset", "earthrise")}
    events = []
    t = (timeline["time_utc"] - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy()
    for body, (set_name, rise_name) in names.items():
        level = timeline[f"{body}_margin"].to_numpy() + timeline[f"{body}_radius"].to_numpy()
        for i in np.where(np.sign(level[:-1]) != np.sign(level[1:]))[0]:
            if level[i] == level[i + 1]:
                continue
            frac = level[i] / (level[i] - level[i + 1])
            when = pd.to_datetime(t[i] + frac * (t[i + 1] - t[i]), unit="s").round("min")
            events.append({"time_utc": when, "event": set_name if level[i] > 0 else rise_name})
    return pd.DataFrame(events, columns=["time_utc", "event"]).sort_values("time_utc", ignore_index=True)


def longest_run(flags):
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def landing_date_summary(site, timeline, events):
    """Sun and Earth hours in the first PLAN_DAYS after landing, for every possible landing day."""
    hours = PLAN_DAYS * 24
    sunsets = events.loc[events["event"] == "sunset", "time_utc"].to_numpy()
    rows = []
    for start in range(0, len(timeline) - hours + 1, 24):
        window = timeline.iloc[start:start + hours]
        t0 = window["time_utc"].iloc[0]
        later = sunsets[sunsets >= np.datetime64(t0)]
        first = (later[0] - np.datetime64(t0)) / np.timedelta64(1, "h") if later.size else np.nan
        rows.append({
            "site": site["name"],
            "landing_utc": t0,
            "sun_hours": int(window["sun_up"].sum()),
            "sun_full_disk_equiv_hours": round(float(window["sun_visible_frac"].sum()), 1),
            "earth_hours": int(window["earth_up"].sum()),
            "sun_and_earth_hours": int(window["both_up"].sum()),
            "longest_sunlit_hours": longest_run(window["sun_up"]),
            "hours_to_first_sunset": round(float(first), 1) if first <= hours else np.nan,
        })
    return rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    for site in SITES:
        run = "plan" if site["kind"] == "planning" else "replay"
        timeline = build_timeline(site, run)
        events = find_events(timeline)
        name = slug(site["name"])
        timeline.to_csv(OUT_DIR / f"{name}_{run}_timeline.csv", index=False)
        events.to_csv(OUT_DIR / f"{name}_{run}_events.csv", index=False)
        print(f"{site['name']:18s} rows {len(timeline):5d} | Sun up {timeline['sun_up'].mean() * 100:5.1f}% "
              f"| Earth up {timeline['earth_up'].mean() * 100:5.1f}% | events {len(events)}")
        if site["kind"] == "planning":
            summary.extend(landing_date_summary(site, timeline, events))

    summary = pd.DataFrame(summary)
    summary.to_csv(OUT_DIR / "planning_summary.csv", index=False)
    print(f"\nLanding-date comparison: {summary['landing_utc'].nunique()} landing days per site "
          f"({summary['landing_utc'].min():%d %b %Y} to {summary['landing_utc'].max():%d %b %Y})")
    stats = summary.groupby("site")[["sun_hours", "earth_hours", "sun_and_earth_hours"]].agg(["min", "max"])
    print(stats.to_string())
    print("\nAll results saved in", OUT_DIR)


if __name__ == "__main__":
    main()