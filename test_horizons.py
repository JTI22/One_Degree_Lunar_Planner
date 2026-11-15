"""Test: get Sun position from the IM-2 site on the Moon for one day."""
from astroquery.jplhorizons import Horizons

site = {"lon": 29.13, "lat": -84.78, "elevation": 0, "body": 301}  # on the Moon
sun = Horizons(
    id="10",  # 10 = the Sun
    location=site,
    epochs={"start": "2026-11-14", "stop": "2026-11-15", "step": "1h"},
)
eph = sun.ephemerides()
print(eph["datetime_str", "AZ", "EL"][:10])
print("Horizons works. Rows:", len(eph))