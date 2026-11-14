"""Landing sites used by One Degree: planning candidates and historical landers."""

from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
SITES_CSV = PROJECT_DIR / "data" / "sites.csv"

# Terrain source: dem80 = LOLA 80 m (80-90 S), dem240 = LOLA 240 m (60-90 S), flat = no terrain.
SITES = [
    {"name": "Mons Mouton", "lat": -84.78, "lon": 29.13, "kind": "planning", "map": "dem80",
     "source": "IM-2 target region, Mons Mouton Plateau"},
    {"name": "Malapert Massif", "lat": -85.99, "lon": -2.93, "kind": "planning", "map": "dem80",
     "source": "LROC QuickMap, Constellation Program Targets (Tier 1)"},
    {"name": "Nobile Rim 1", "lat": -85.43, "lon": 37.37, "kind": "planning", "map": "dem80",
     "source": "LROC QuickMap, A3 Candidate Landing Regions 2022 (region centre)"},
    {"name": "Odysseus (IM-1)", "lat": -80.12760, "lon": 1.43670, "kind": "replay", "map": "dem240",
     "source": "LROC QuickMap, Anthropogenic Features"},
    {"name": "Blue Ghost M1", "lat": 18.56220, "lon": 61.81020, "kind": "replay", "map": "flat",
     "source": "LROC QuickMap, Anthropogenic Features"},
    {"name": "Athena (IM-2)", "lat": -84.79060, "lon": 29.19567, "kind": "replay", "map": "dem80",
     "source": "LROC QuickMap, Anthropogenic Features"},
]

PLANNING_WINDOW = ("2026-11-15", "2027-01-01")

REPLAY_WINDOWS = {
    "Odysseus (IM-1)": ("2024-02-22 20:00", "2024-03-06 00:00"),
    "Blue Ghost M1": ("2025-03-02 06:00", "2025-03-17 06:00"),
    "Athena (IM-2)": ("2025-03-06 12:00", "2025-03-08 00:00"),
}


def main():
    sites = pd.DataFrame(SITES)
    SITES_CSV.parent.mkdir(parents=True, exist_ok=True)
    sites.to_csv(SITES_CSV, index=False)
    print(sites.to_string(index=False))
    print(f"\nSaved {len(sites)} sites to {SITES_CSV}")


if __name__ == "__main__":
    main()