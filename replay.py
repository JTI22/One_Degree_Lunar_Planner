"""Mission Replay: compare predicted Sun and Earth conditions with what happened to real landers."""

from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_DIR / "data" / "results"

MISSIONS = [
    {"site": "Odysseus (IM-1)", "landed_utc": "2024-02-22 23:24", "end_utc": "2024-02-29 12:00",
     "end_precision_h": 12, "end_event": "Mission ended with onset of lunar night (announced 29 Feb)",
     "source": "Intuitive Machines; Universe Today, 2024"},
    {"site": "Blue Ghost M1", "landed_utc": "2025-03-02 08:34", "end_utc": "2025-03-16 23:15",
     "end_precision_h": 0.5, "end_event": "Final data, ~5 h after local sunset",
     "source": "Firefly Aerospace, 17 Mar 2025"},
    {"site": "Athena (IM-2)", "landed_utc": "2025-03-06 17:28", "end_utc": "2025-03-07 06:15",
     "end_precision_h": 0.5, "end_event": "Last contact; batteries depleted, lander on its side",
     "source": "NASA / Intuitive Machines, Mar 2025"},
]


def slug(name):
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def replay(mission):
    name = slug(mission["site"])
    timeline = pd.read_csv(RESULTS_DIR / f"{name}_replay_timeline.csv", parse_dates=["time_utc"])
    events = pd.read_csv(RESULTS_DIR / f"{name}_replay_events.csv", parse_dates=["time_utc"])
    landed = pd.Timestamp(mission["landed_utc"])
    end = pd.Timestamp(mission["end_utc"])

    after_landing = events[events["time_utc"] >= landed]
    sunsets = after_landing.loc[after_landing["event"] == "sunset", "time_utc"]
    predicted_sunset = sunsets.min() if not sunsets.empty else pd.NaT

    active = timeline[(timeline["time_utc"] >= landed) & (timeline["time_utc"] <= end)]
    gap = (end - predicted_sunset).total_seconds() / 3600 if pd.notna(predicted_sunset) else None

    return {
        "site": mission["site"],
        "landed_utc": landed,
        "predicted_sunset_utc": predicted_sunset,
        "actual_end_utc": end,
        "end_precision_h": mission["end_precision_h"],
        "end_minus_sunset_h": None if gap is None else round(gap, 1),
        "sun_visible_pct_while_active": round(active["sun_visible_frac"].mean() * 100, 1),
        "earth_visible_pct_while_active": round(active["earth_up"].mean() * 100, 1),
        "end_event": mission["end_event"],
        "source": mission["source"],
    }


def main():
    rows = [replay(m) for m in MISSIONS]
    table = pd.DataFrame(rows)
    table.to_csv(RESULTS_DIR / "mission_replay.csv", index=False)
    show = ["site", "predicted_sunset_utc", "actual_end_utc", "end_minus_sunset_h",
            "sun_visible_pct_while_active", "earth_visible_pct_while_active"]
    print(table[show].to_string(index=False))
    print("\nend_minus_sunset_h > 0: lander outlived predicted sunset; < 0: it stopped before sunset.")
    print("Saved", RESULTS_DIR / "mission_replay.csv")


if __name__ == "__main__":
    main()