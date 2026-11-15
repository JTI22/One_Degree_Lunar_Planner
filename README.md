# One Degree — Terrain-Aware Lunar Landing Planner

- **Live app:** https://onedegreelunarplanner.streamlit.app/
- **Challenge:** NASA Space Apps Challenge 2026 — Lunar Landing Site Navigator (CLPS)
- **Team:** OneXDegree

At the lunar south pole the Sun skims only a few degrees above the horizon. A single ridge can decide whether a
lander has sunlight and a direct view of Earth. One Degree combines NASA LOLA terrain with JPL Horizons ephemerides
to compare landing sites and landing dates, and tests its predictions against three real lunar landers.

---

## The problem

Mission planners must choose a landing site and date that give a lander enough sunlight and a direct view of Earth.
Standard sky calculations assume a flat horizon. Near the south pole this is not enough: nearby terrain often rises
higher than the Sun itself, and small changes in site or date can change conditions by hundreds of hours.

## What the app does

| Tab | Purpose |
|---|---|
| **Compare sites & dates** | Pick any landing day (15 Nov 2026 – Dec 2027) and compare Sun, Earth and combined hours in the first 30 days at three candidate sites, plus the effect of +1, +7 and +14 day launch slips |
| **Local sky** | The terrain horizon in every direction, with the Sun and Earth paths drawn over it; a time slider shows any moment |
| **Timeline** | Sun and Earth disk visibility over time, with rise and set times interpolated to the minute |
| **Mission Replay** | The same model applied to Odysseus (IM-1), Blue Ghost Mission 1 and Athena (IM-2), compared with what happened |
| **Method & validation** | Pipeline, three independent checks against NASA data, limits and references |

## Key results

- **Site choice matters.** Over one year, Mons Mouton sees the Sun 47.5% of the time and Earth 92.9%. The Malapert
  Massif target point sees the Sun 44.1% of the time but never sees Earth, because a ridge to its north blocks it.
- **Landing date matters.** At Mons Mouton, the hours with both Sun and Earth in the first 30 days range from 194 h
  to 393 h depending on the landing day.
- **Mission Replay.**
  - *Odysseus:* contact ended about 52 h before our predicted terrain sunset, while the Sun was fully visible.
    Terrain did not end this mission, which is consistent with the tipped lander's panels losing light.
  - *Blue Ghost:* final data arrived 2.9 h after our predicted terrain sunset; Firefly reports about 5 h.
    Adding real terrain moved the prediction 33 minutes closer than a flat-horizon estimate.
  - *Athena:* the model predicts full sunlight, but the lander lay on its side in a ~20 m crater, smaller than one
    map pixel. This is shown openly as a limit of the model.

## Validation

1. **Ground height** at three lander sites matches LROC QuickMap within 0.2–1.4 m.
2. **Site ranking** for Sun and Earth visibility matches NASA's LOLA long-term visibility maps (18.6-year averages).
   At Mons Mouton and Malapert our Sun values agree within 1%.
3. **NASA Earth Visibility map images** (LROC QuickMap) show Mons Mouton bright and Malapert dark, matching our results.

## How it works

1. **Sites** — three planning sites and three real landers, with positions from LROC QuickMap.
2. **Sun and Earth positions** — JPL Horizons with an observer on the lunar surface (body 301): azimuth, elevation
   and apparent disk size, hourly for planning and every 10 minutes for replays.
3. **Terrain horizon** — for 720 directions, rays follow great circles for 150 km across NASA LOLA elevation models
   (80 m, 240 m and 474 m). The horizon is the highest apparent terrain angle, using exact spherical geometry and a
   2 m observer height.
4. **Visibility** — the fraction of the Sun or Earth disk above the terrain (circular-segment geometry). Rise and
   set times are interpolated between samples.
5. **Comparison** — every landing day, launch slips, and Mission Replay.

## Run it

**App only** (uses the precomputed results in `data/`):

```
pip install -r requirements.txt
streamlit run app.py
```

**Full pipeline** (recomputes everything):

```
pip install -r requirements-pipeline.txt
```

Download these elevation models into `data/dem/` (not stored in this repository because of their size):
- `LDEM_80S_80MPP_ADJ` and `LDEM_60S_240MPP_ADJ` (GeoTIFF) from [NASA GSFC PGDA product 90](https://pgda.gsfc.nasa.gov/products/90)
- `LDEM_64.IMG` and `LDEM_64.LBL` from the [LOLA GDR archive](https://imbrium.mit.edu/DATA/LOLA_GDR/CYLINDRICAL/IMG/)

Then run in order:

```
python sites.py
python fetch_horizons.py
python horizon_mask.py
python visibility.py
python replay.py
python plot_sky.py
```

## Project files

| File | Purpose |
|---|---|
| `sites.py` | Landing sites, sources and time windows |
| `fetch_horizons.py` | Sun and Earth positions from JPL Horizons |
| `horizon_mask.py` | Terrain horizon in 720 directions from LOLA elevation models |
| `visibility.py` | Disk visibility, rise/set events and landing-date comparison |
| `replay.py` | Mission Replay against real landers |
| `plot_sky.py` | Static sky plots |
| `app.py` | Streamlit web app |
| `view_dem.py`, `test_horizons.py` | Setup checks for the terrain map and Horizons access |

## Limits

- Results describe **geometric visibility** (sunlight availability and Earth visibility), not power output or a
  guaranteed radio link. Panel orientation, link budgets and antennas are not modelled.
- Terrain smaller than a map pixel is not resolved.
- The horizon is treated as straight across each disk; this is approximate for Earth (~2° wide).
- Mission end times come from public statements; Odysseus has a date only (±12 h).

## References and credits

**Data**
- Barker, M. K., et al. (2023). A new view of the lunar south pole from the Lunar Orbiter Laser Altimeter (LOLA).
  *The Planetary Science Journal*, 4, 183. [NASA GSFC PGDA product 90](https://pgda.gsfc.nasa.gov/products/90)
- LRO LOLA Gridded Data Record, LDEM_64, NASA Planetary Data System. [LOLA GDR archive](https://imbrium.mit.edu/DATA/LOLA_GDR/CYLINDRICAL/IMG/)
- [JPL Horizons](https://ssd.jpl.nasa.gov/horizons/), NASA Jet Propulsion Laboratory
- [LROC QuickMap](https://quickmap.lroc.im-ldi.com/) (NASA LRO / Arizona State University): site positions, ground
  heights, LOLA Sun and Earth Visibility layers, and the two map screenshots in `data/figures/`

**Method**
- Mazarico, E., et al. (2011). Illumination conditions of the lunar polar regions using LOLA topography.
  *Icarus*, 211, 1066–1081. [NASA NTRS](https://ntrs.nasa.gov/citations/20120010094)

**Mission facts**
- Odysseus (IM-1): landing — [NASA Artemis blog, 22 Feb 2024](https://www.nasa.gov/blogs/artemis/2024/02/22/);
  end — [Universe Today, 2024](https://universetoday.com/166340/lunar-night-permanently-ends-the-odysseus-mission),
  [UPI, 27 Feb 2024](https://www.upi.com/Science_News/2024/02/27/odysseus-moon-landing-mission-cut-short/3691709083948/)
- Blue Ghost Mission 1: landing — [NASA, 2 Mar 2025](https://www.nasa.gov/news-release/touchdown-carrying-nasa-science-fireflys-blue-ghost-lands-on-moon/);
  end — [Firefly Aerospace, 17 Mar 2025](https://fireflyspace.com/news/firefly-aerospace-successfully-completes-14-days-of-surface-operations-on-the-moon)
- Athena (IM-2): landing and end — [SpacePolicyOnline, 7 Mar 2025](https://spacepolicyonline.com/news/im-2-mission-ends-one-day-after-lunar-landing/);
  [Spaceflight Now, 7 Mar 2025](https://spaceflightnow.com/2025/03/07/intuitive-machines-im-2-mission-ends-with-lander-on-its-side-on-the-moon/)

**Software**
- Python, Streamlit, pandas, NumPy, SciPy, Plotly, Matplotlib, Pillow, rasterio, pyproj, astroquery and Astropy.

## Use of Super Intelligence (SI) tools

This project used SI tools in line with the NASA Space Apps Challenge SI policy.

- **Tools:** Claude (Anthropic) and ChatGPT (OpenAI).
- **How they were used:** explaining scientific concepts and methods; helping locate and understand data sources;
  suggesting options during brainstorming; drafting, reviewing and debugging code; helping interpret results; and
  editing written text, including this README.
- **What the team did:** chose the challenge and the problem to focus on; decided the scope, approach and features;
  selected the landing sites and missions; collected site positions and validation values from LROC QuickMap;
  ran, checked and customised every step of the code; reviewed all text; and made all final decisions.
- **Results:** all numbers and figures come from running this code on the cited NASA data. They were not
  generated by SI.
- **Media:** no SI-generated images, video or audio are used. The two map images are credited screenshots
  from LROC QuickMap.

This is a student project for the NASA Space Apps Challenge 2026. It uses no NASA logos or branding and is not
endorsed by NASA.
