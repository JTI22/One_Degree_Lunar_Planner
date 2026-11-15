"""Time-step check: compare hourly Sun results with 10-minute results over a difficult window."""

from pathlib import Path

import numpy as np
import pandas as pd

from fetch_horizons import fetch
from sites import SITES
from visibility import disk_fraction, horizon_at, slug

PROJECT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_DIR / "data" / "results"
MASK_DIR = PROJECT_DIR / "data" / "masks"

SITE = "Malapert Massif"
WINDOW = ("2027-02-01", "2027-02-12")
MATCH_HOURS = 2.0


def sun_events(time_utc, level):
    """Interpolated times when the whole Sun disk sets (level falls through 0) or rises."""
    t = (time_utc - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy()
    level = np.asarray(level)
    rows = []
    for i in np.where(np.sign(level[:-1]) != np.sign(level[1:]))[0]:
        if level[i] == level[i + 1]:
            continue
        frac = level[i] / (level[i] - level[i + 1])
        when = pd.to_datetime(t[i] + frac * (t[i + 1] - t[i]), unit="s").round("min")
        rows.append({"time_utc": when, "event": "sunset" if level[i] > 0 else "sunrise"})
    return pd.DataFrame(rows, columns=["time_utc", "event"])


def main():
    site = next(s for s in SITES if s["name"] == SITE)
    mask = pd.read_csv(MASK_DIR / f"{slug(SITE)}.csv")

    fine = fetch("10", site, WINDOW[0], WINDOW[1], "10m")
    fine["margin"] = fine["el_deg"] - horizon_at(mask, fine["az_deg"])
    fine["sun_visible_frac"] = disk_fraction(fine["margin"], fine["radius_deg"])
    fine_events = sun_events(fine["time_utc"], fine["margin"] + fine["radius_deg"])

    hourly = pd.read_csv(RESULTS_DIR / f"{slug(SITE)}_plan_timeline.csv", parse_dates=["time_utc"])
    hourly = hourly[(hourly["time_utc"] >= WINDOW[0]) & (hourly["time_utc"] <= WINDOW[1])].reset_index(drop=True)
    hourly_events = sun_events(hourly["time_utc"], hourly["sun_margin"] + hourly["sun_radius"])

    rows = []
    for _, event in fine_events.iterrows():
        same = hourly_events[hourly_events["event"] == event["event"]]
        gaps = (same["time_utc"] - event["time_utc"]).abs().dt.total_seconds() / 3600
        found = (not gaps.empty) and gaps.min() <= MATCH_HOURS
        rows.append({"time_utc_10min": event["time_utc"], "event": event["event"],
                     "found_by_hourly": found,
                     "difference_min": round(gaps.min() * 60, 1) if found else np.nan})
    table = pd.DataFrame(rows)

    summary = pd.DataFrame([{
        "site": SITE, "window_start": WINDOW[0], "window_end": WINDOW[1],
        "sun_up_pct_10min": round((fine["sun_visible_frac"] > 0).mean() * 100, 1),
        "sun_up_pct_hourly": round((hourly["sun_visible_frac"] > 0).mean() * 100, 1),
        "events_10min": len(fine_events), "events_hourly": len(hourly_events),
        "events_missed_by_hourly": int((~table["found_by_hourly"]).sum()) if not table.empty else 0,
        "max_timing_difference_min": table["difference_min"].max() if not table.empty else np.nan,
    }])
    table.to_csv(RESULTS_DIR / "time_step_check_events.csv", index=False)
    summary.to_csv(RESULTS_DIR / "time_step_check.csv", index=False)
    print(summary.T.to_string(header=False))
    print()
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()