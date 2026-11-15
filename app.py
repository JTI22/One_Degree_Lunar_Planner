"""One Degree: terrain-aware Sun and Earth visibility for lunar landing sites."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, ImageOps

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
RESULTS_DIR = DATA_DIR / "results"
MASK_DIR = DATA_DIR / "masks"
FIGURES_DIR = DATA_DIR / "figures"

SUN_COLOR = "#f2a900"
EARTH_COLOR = "#3d8bfd"
TERRAIN_COLOR = "rgba(140, 123, 107, 0.85)"
SITE_COLORS = {"Mons Mouton": "#2ec4b6", "Malapert Massif": "#b388ff", "Nobile Rim 1": "#ff8a65"}

QUICKMAP_REFERENCE = pd.DataFrame([
    {"site": "Mons Mouton", "nasa_sun_pct": 46.7, "nasa_earth_pct": 93.3, "note": "Read at IM-2 Athena lander point"},
    {"site": "Malapert Massif", "nasa_sun_pct": 44.8, "nasa_earth_pct": 4.6, "note": "Read ~5 km from target point"},
    {"site": "Nobile Rim 1", "nasa_sun_pct": 37.8, "nasa_earth_pct": 46.2, "note": "Read near region centre"},
])

HEIGHT_CHECK = pd.DataFrame([
    {"site": "Athena (IM-2)", "terrain_map": "LOLA 80 m", "our_ground_m": 5321.5, "quickmap_m": 5321.3},
    {"site": "Odysseus (IM-1)", "terrain_map": "LOLA 240 m", "our_ground_m": 2581.8, "quickmap_m": 2580.4},
    {"site": "Blue Ghost M1", "terrain_map": "LOLA global 474 m", "our_ground_m": -3650.2, "quickmap_m": -3650.0},
])

st.set_page_config(page_title="One Degree | Lunar Landing Planner", page_icon="🌗", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1250px; padding-top: 2.2rem;}
h1 {letter-spacing: 0.5px;}
.tagline {color: #a9b1bd; font-size: 1.05rem; margin-top: -0.6rem; margin-bottom: 1.2rem;}
div[data-testid="stMetric"] {
    background: #151a23; border: 1px solid #262d3a; border-radius: 10px; padding: 0.7rem 0.9rem;
}
div[data-testid="stMetricLabel"] p {color: #a9b1bd;}
button[data-baseweb="tab"] p {font-size: 1rem;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def slug(name):
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


@st.cache_data
def load_sites():
    return pd.read_csv(DATA_DIR / "sites.csv")


@st.cache_data
def load_mask(site):
    return pd.read_csv(MASK_DIR / f"{slug(site)}.csv")


@st.cache_data
def load_timeline(site, run):
    return pd.read_csv(RESULTS_DIR / f"{slug(site)}_{run}_timeline.csv", parse_dates=["time_utc"])


@st.cache_data
def load_events(site, run):
    return pd.read_csv(RESULTS_DIR / f"{slug(site)}_{run}_events.csv", parse_dates=["time_utc"])


@st.cache_data
def load_csv(name):
    return pd.read_csv(RESULTS_DIR / name)


def sky_figure(mask, timeline, moment=None, title=""):
    floor = min(mask["horizon_deg"].min(), timeline["sun_el"].min(), timeline["earth_el"].min()) - 1
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mask["az_deg"], y=[floor] * len(mask), mode="lines",
                             line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=mask["az_deg"], y=mask["horizon_deg"], mode="lines", fill="tonexty",
                             fillcolor=TERRAIN_COLOR, line=dict(color="#6b5a4b", width=1),
                             name="Terrain horizon", hovertemplate="Az %{x:.1f}°<br>Terrain %{y:.2f}°<extra></extra>"))
    for body, color, label in (("sun", SUN_COLOR, "Sun path"), ("earth", EARTH_COLOR, "Earth path")):
        fig.add_trace(go.Scattergl(x=timeline[f"{body}_az"], y=timeline[f"{body}_el"], mode="markers",
                                   marker=dict(size=3, color=color), name=label,
                                   customdata=timeline["time_utc"].dt.strftime("%Y-%m-%d %H:%M"),
                                   hovertemplate="%{customdata} UTC<br>Az %{x:.1f}°, El %{y:.2f}°<extra></extra>"))
    if moment is not None:
        for body, color, label in (("sun", SUN_COLOR, "Sun now"), ("earth", EARTH_COLOR, "Earth now")):
            fig.add_trace(go.Scatter(x=[moment[f"{body}_az"]], y=[moment[f"{body}_el"]], mode="markers",
                                     marker=dict(size=16, color=color, line=dict(color="white", width=2)),
                                     name=label))
    fig.update_layout(title=title, height=430, margin=dict(l=10, r=10, t=50, b=10),
                      xaxis=dict(title="Direction (azimuth)", range=[0, 360], tickvals=list(range(0, 361, 45)),
                                 ticktext=["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]),
                      yaxis=dict(title="Elevation (deg)", range=[floor, None]),
                      legend=dict(orientation="h", y=-0.2))
    return fig


def timeline_figure(timeline, markers=(), x_range=None):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timeline["time_utc"], y=timeline["sun_visible_frac"] * 100, mode="lines",
                             fill="tozeroy", line=dict(color=SUN_COLOR), name="Sun disk visible (%)"))
    fig.add_trace(go.Scatter(x=timeline["time_utc"], y=timeline["earth_visible_frac"] * 100, mode="lines",
                             line=dict(color=EARTH_COLOR, width=2), name="Earth disk visible (%)"))
    for i, (when, label, color) in enumerate(markers):
        fig.add_shape(type="line", x0=when, x1=when, y0=0, y1=1, yref="paper",
                      line=dict(color=color, dash="dash", width=2))
        fig.add_annotation(x=when, y=1.03 + 0.07 * i, yref="paper", text=label, showarrow=False,
                           font=dict(color=color, size=12))
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=70, b=10), yaxis=dict(title="Visible (%)", range=[0, 105]),
                      xaxis=dict(title="Time (UTC)", range=x_range), legend=dict(orientation="h", y=-0.25))
    return fig


sites = load_sites()
planning = sites[sites["kind"] == "planning"]["name"].tolist()
replays = sites[sites["kind"] == "replay"]["name"].tolist()

st.title("🌗 One Degree")
st.markdown('<p class="tagline">At the lunar south pole the Sun skims a few degrees above the horizon. '
            'One ridge decides whether a lander has sunlight and a view of Earth.</p>', unsafe_allow_html=True)
st.markdown("**Terrain-aware Sun and Earth visibility for lunar landing sites.** This tool combines NASA LOLA "
            "terrain with JPL Horizons ephemerides to compare sites and landing dates, and tests its predictions "
            "against real landers.")

tab_compare, tab_sky, tab_timeline, tab_replay, tab_method = st.tabs(
    ["Compare sites & dates", "Local sky", "Timeline", "Mission Replay", "Method & validation"])

with tab_compare:
    summary = load_csv("planning_summary.csv")
    summary["landing_utc"] = pd.to_datetime(summary["landing_utc"])
    days = sorted(summary["landing_utc"].dt.date.unique())
    landing = st.date_input("Planned landing date (00:00 UTC)", value=days[0], min_value=days[0],
                            max_value=days[-1], key="landing_date")
    landing = pd.Timestamp(landing)
    st.caption(f"Totals over the first 30 days on the surface after landing on {landing:%d %b %Y}. "
               f"Any landing day from {days[0]:%d %b %Y} to {days[-1]:%d %b %Y} can be compared.")

    chosen = summary[summary["landing_utc"] == landing]
    cols = st.columns(len(chosen))
    for col, (_, row) in zip(cols, chosen.iterrows()):
        col.subheader(row["site"])
        col.metric("Sun above terrain", f"{row['sun_hours']} h")
        col.metric("Earth above terrain", f"{row['earth_hours']} h")
        col.metric("Sun and Earth together", f"{row['sun_and_earth_hours']} h")
        first = row["hours_to_first_sunset"]
        col.metric("First sunset after landing", "none in 30 days" if pd.isna(first) else f"{first:.0f} h")

    st.markdown("**What a launch slip would change**")
    rows = []
    for slip in (0, 1, 7, 14):
        day = landing + pd.Timedelta(days=slip)
        for _, row in summary[summary["landing_utc"] == day].iterrows():
            rows.append({"Site": row["site"], "Landing": "As planned" if slip == 0 else f"+{slip} d",
                         "Sun and Earth (h)": row["sun_and_earth_hours"],
                         "First sunset (h)": row["hours_to_first_sunset"]})
    if rows:
        slips = pd.DataFrame(rows)
        order = [c for c in ["As planned", "+1 d", "+7 d", "+14 d"] if c in slips["Landing"].unique()]
        both = slips.pivot(index="Site", columns="Landing", values="Sun and Earth (h)")[order]
        sunset = slips.pivot(index="Site", columns="Landing", values="First sunset (h)")[order]
        c1, c2 = st.columns(2)
        c1.caption("Hours with both Sun and Earth above the terrain (first 30 days)")
        c1.dataframe(both.style.format("{:.0f} h"), width="stretch")
        c2.caption("Hours from landing to the first terrain sunset")
        c2.dataframe(sunset.style.format("{:.0f} h", na_rep="none"), width="stretch")
        if len(order) < 4:
            st.caption("Some delays fall outside the computed date range.")

    metric = st.radio("Show across all landing dates", ["Sun and Earth together", "Sun above terrain",
                                                        "Earth above terrain"],
                      horizontal=True, key="trend_metric")
    column = {"Sun and Earth together": "sun_and_earth_hours", "Sun above terrain": "sun_hours",
              "Earth above terrain": "earth_hours"}[metric]
    trend = go.Figure()
    for site_name, group in summary.groupby("site", sort=False):
        trend.add_trace(go.Scatter(x=group["landing_utc"], y=group[column], mode="lines", name=site_name,
                                   line=dict(color=SITE_COLORS.get(site_name), width=2.5)))
    trend.add_shape(type="line", x0=landing, x1=landing, y0=0, y1=1, yref="paper",
                    line=dict(color="#e8e6e1", dash="dash", width=1.5))
    trend.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="Landing date (UTC)",
                        yaxis_title="Hours in first 30 days (of 720)", legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(trend, width="stretch")
    st.caption("Each point is one possible landing day. The dashed line marks the selected date.")

with tab_sky:
    site = st.selectbox("Site", planning + replays, key="sky_site")
    run = "plan" if site in planning else "replay"
    timeline = load_timeline(site, run)
    mask = load_mask(site)
    labels = timeline["time_utc"].dt.strftime("%Y-%m-%d %H:%M").tolist()
    chosen_time = st.select_slider("Moment (UTC) — drag to move the Sun and Earth", options=labels,
                                   value=labels[0], key="sky_time")
    moment = timeline.iloc[labels.index(chosen_time)]
    c1, c2, c3 = st.columns(3)
    c1.metric("Time (UTC)", f"{moment['time_utc']:%Y-%m-%d %H:%M}")
    c2.metric("Sun disk visible", f"{moment['sun_visible_frac'] * 100:.0f}%",
              f"{moment['sun_margin']:+.2f}° vs terrain")
    c3.metric("Earth disk visible", f"{moment['earth_visible_frac'] * 100:.0f}%",
              f"{moment['earth_margin']:+.2f}° vs terrain")
    st.plotly_chart(sky_figure(mask, timeline, moment, f"{site}: terrain horizon with Sun and Earth paths"),
                    width="stretch")
    st.caption("Brown: highest terrain in each direction (720 directions, 150 km of LOLA terrain). "
               "A body is hidden whenever its path dips into the brown area.")

with tab_timeline:
    site = st.selectbox("Site", planning + replays, key="tl_site")
    run = "plan" if site in planning else "replay"
    timeline = load_timeline(site, run)
    events = load_events(site, run)
    c1, c2, c3 = st.columns(3)
    c1.metric("Sun above terrain", f"{timeline['sun_up'].mean() * 100:.0f}% of the time")
    c2.metric("Earth above terrain", f"{timeline['earth_up'].mean() * 100:.0f}% of the time")
    c3.metric("Both together", f"{timeline['both_up'].mean() * 100:.0f}% of the time")
    st.plotly_chart(timeline_figure(timeline), width="stretch")
    st.markdown("**Rise and set events above the terrain** (interpolated to the minute)")
    if events.empty:
        st.info("No rise or set events in this window.")
    else:
        shown = events.copy()
        shown["time_utc"] = shown["time_utc"].dt.strftime("%Y-%m-%d %H:%M")
        shown.columns = ["Time (UTC)", "Event"]
        st.dataframe(shown, width="stretch", hide_index=True)
        st.caption("Short set-and-rise pairs happen when the Sun skims along a ridge line.")

with tab_replay:
    replay = load_csv("mission_replay.csv")
    for column in ("landed_utc", "predicted_sunset_utc", "actual_end_utc"):
        replay[column] = pd.to_datetime(replay[column])
    st.markdown("We ran the same model for three real landers and compared it with what happened. "
                "Each mission tests a different claim.")
    table = replay[["site", "landed_utc", "predicted_sunset_utc", "actual_end_utc", "end_minus_sunset_h",
                    "sun_visible_pct_while_active", "earth_visible_pct_while_active"]].copy()
    for column in ("landed_utc", "predicted_sunset_utc", "actual_end_utc"):
        table[column] = table[column].dt.strftime("%Y-%m-%d %H:%M").fillna("none in window")
    table["end_minus_sunset_h"] = table["end_minus_sunset_h"].map(lambda v: "—" if pd.isna(v) else f"{v:+.1f}")
    table.columns = ["Lander", "Landed (UTC)", "Predicted terrain sunset (UTC)", "Actual end (UTC)",
                     "End − sunset (h)", "Sun visible while active (%)", "Earth visible while active (%)"]
    st.dataframe(table, width="stretch", hide_index=True)

    for _, row in replay.iterrows():
        st.subheader(row["site"])
        timeline = load_timeline(row["site"], "replay")
        markers = [(row["landed_utc"], "Landed", "#43a047"), (row["actual_end_utc"], "Mission end", "#e53935")]
        if pd.notna(row["predicted_sunset_utc"]):
            markers.append((row["predicted_sunset_utc"], "Predicted sunset", "#b388ff"))
        st.plotly_chart(timeline_figure(timeline, markers), width="stretch")
        gap = row["end_minus_sunset_h"]
        if pd.notna(gap) and abs(gap) < 24:
            start = min(row["predicted_sunset_utc"], row["actual_end_utc"]) - pd.Timedelta(hours=8)
            stop = max(row["predicted_sunset_utc"], row["actual_end_utc"]) + pd.Timedelta(hours=4)
            st.caption("Zoom on the final hours")
            st.plotly_chart(timeline_figure(timeline, markers[1:], x_range=[start, stop]), width="stretch")
        if row["site"].startswith("Blue Ghost"):
            st.markdown(f"**Tests:** sunset timing. Firefly reports final data about 5 h after local sunset. "
                        f"Our model puts the end **{gap:.1f} h** after predicted terrain sunset. Terrain here comes "
                        "from the 474 m global LOLA map, so hills smaller than a pixel are not modelled.")
        elif pd.isna(gap):
            st.markdown(f"**Tests:** the limits of the terrain model. Our 80 m terrain predicts the Sun was visible "
                        f"**{row['sun_visible_pct_while_active']:.0f}%** of the time while the lander was active. "
                        "Athena came to rest on its side inside a ~20 m crater, smaller than one map pixel, so the "
                        "model cannot represent the shadow it lay in.")
        else:
            st.markdown(f"**Tests:** whether terrain sunset ended the mission. The lander stopped **{abs(gap):.0f} h "
                        f"before** our predicted terrain sunset, while the Sun was visible "
                        f"**{row['sun_visible_pct_while_active']:.0f}%** of the time. Terrain did not end this "
                        "mission; the early end is consistent with the tipped lander's panels losing light.")
        st.caption(f"Mission facts: {row['end_event']}. Source: {row['source']}.")

with tab_method:
    st.markdown("""
**Pipeline**
1. **Sites:** planning candidates and real landers, positions from LROC QuickMap.
2. **Sun and Earth positions:** JPL Horizons, observer on the lunar surface (body 301), azimuth and elevation hourly
   (planning) or every 10 minutes (replay), plus apparent disk size.
3. **Terrain horizon:** for 720 directions, rays follow great circles for 150 km across NASA LOLA elevation models;
   the horizon is the highest apparent terrain angle, using exact spherical geometry and a 2 m observer height.
4. **Visibility:** the fraction of the Sun or Earth disk above the terrain (circular-segment geometry); rise and set
   times are interpolated between samples.
5. **Comparison:** every landing day from 15 Nov 2026 to Dec 2027 (first 30 days on the surface), launch slips of
   +1, +7 and +14 days, and Mission Replay against three real landers.
""")
    st.markdown("**Validation 1 — ground height against LROC QuickMap**")
    check = HEIGHT_CHECK.copy()
    check["difference_m"] = (check["our_ground_m"] - check["quickmap_m"]).round(1)
    check.columns = ["Site", "Terrain map", "Our ground height (m)", "QuickMap (m)", "Difference (m)"]
    st.dataframe(check, width="stretch", hide_index=True)

    st.markdown("**Validation 2 — site ranking against NASA LOLA long-term visibility maps (QuickMap)**")
    rows = []
    for site in planning:
        timeline = load_timeline(site, "plan")
        rows.append({"site": site, "our_sun_pct": round(timeline["sun_up"].mean() * 100, 1),
                     "our_earth_pct": round(timeline["earth_up"].mean() * 100, 1)})
    compare = pd.DataFrame(rows).merge(QUICKMAP_REFERENCE, on="site")
    same_sun = compare.sort_values("our_sun_pct")["site"].tolist() == compare.sort_values("nasa_sun_pct")["site"].tolist()
    same_earth = (compare.sort_values("our_earth_pct")["site"].tolist()
                  == compare.sort_values("nasa_earth_pct")["site"].tolist())
    shown = compare.copy()
    shown.columns = ["Site", "Our Sun (%)", "Our Earth (%)", "NASA Sun (%)", "NASA Earth (%)", "Note"]
    st.dataframe(shown, width="stretch", hide_index=True)
    st.write(f"Same Sun ranking as NASA: **{'yes' if same_sun else 'no'}** · "
             f"Same Earth ranking as NASA: **{'yes' if same_earth else 'no'}**")
    st.caption("NASA values are 18.6-year averages; ours cover 15 Nov 2026 – 1 Jan 2028, "
               "so rankings are the fair comparison, not exact percentages.")

    st.markdown("**Validation 3 — NASA LOLA Earth Visibility map (LROC QuickMap)**")
    our_earth = dict(zip(compare["site"], compare["our_earth_pct"]))
    shots = [
        ("quickmap_monsmouton_earth.png",
         f"Mons Mouton (IM-2 Athena point): bright, Earth visible most of the time. "
         f"NASA ≈ 93%, our model {our_earth.get('Mons Mouton', 0):.0f}%."),
        ("quickmap_malapert_earth.png",
         f"Malapert Massif target point: dark side of the ridge, Earth rarely visible. "
         f"NASA ≈ 5%, our model {our_earth.get('Malapert Massif', 0):.0f}%."),
    ]
    shot_cols = st.columns(len(shots))
    for col, (file_name, caption) in zip(shot_cols, shots):
        path = FIGURES_DIR / file_name
        if path.exists():
            col.image(ImageOps.fit(Image.open(path), (900, 480), centering=(0.0, 1.0)), width="stretch")
            col.caption(caption)
    st.caption("Bright = Earth visible most of the time; dark = rarely visible. Image: LROC QuickMap "
               "(NASA LRO / Arizona State University), LOLA Earth Visibility 240 m layer, accessed 15 Nov 2026.")

    st.markdown("""
**Limits (stated honestly)**
- Results describe **geometric visibility**: sunlight availability and Earth visibility, not power output or a
  guaranteed radio link (no panel orientation, link budget or antenna model).
- Terrain smaller than a map pixel is invisible to the model (80 m, 240 m and 474 m maps).
- The horizon is treated as straight across each disk; this is approximate for Earth (~2° wide).
- Mission end times come from public statements; Odysseus has a date only (±12 h).

**References and credits**

*Data*
- Barker, M. K., et al. (2023). A new view of the lunar south pole from the Lunar Orbiter Laser Altimeter (LOLA).
  *The Planetary Science Journal*, 4, 183. Elevation models: [NASA GSFC PGDA product 90](https://pgda.gsfc.nasa.gov/products/90)
- LRO LOLA Gridded Data Record, global elevation model LDEM_64, NASA Planetary Data System:
  [LOLA GDR archive](https://imbrium.mit.edu/DATA/LOLA_GDR/CYLINDRICAL/IMG/)
- [JPL Horizons](https://ssd.jpl.nasa.gov/horizons/), NASA Jet Propulsion Laboratory — Sun and Earth ephemerides
- [LROC QuickMap](https://quickmap.lroc.im-ldi.com/) (NASA LRO / Arizona State University) — site positions,
  ground heights, LOLA Sun and Earth Visibility layers and the two map images above

*Method*
- Mazarico, E., et al. (2011). Illumination conditions of the lunar polar regions using LOLA topography.
  *Icarus*, 211, 1066–1081. [NASA NTRS](https://ntrs.nasa.gov/citations/20120010094)

*Mission facts*
- Blue Ghost Mission 1: [Firefly Aerospace, 17 Mar 2025](https://fireflyspace.com/news/firefly-aerospace-successfully-completes-14-days-of-surface-operations-on-the-moon)
- Odysseus (IM-1): [Universe Today, 2024](https://universetoday.com/166340/lunar-night-permanently-ends-the-odysseus-mission);
  [UPI, 27 Feb 2024](https://www.upi.com/Science_News/2024/02/27/odysseus-moon-landing-mission-cut-short/3691709083948/)
- Athena (IM-2): [Spaceflight Now, 7 Mar 2025](https://spaceflightnow.com/2025/03/07/intuitive-machines-im-2-mission-ends-with-lander-on-its-side-on-the-moon/)

*Software*
- Python, Streamlit, pandas, NumPy, SciPy, Plotly, Matplotlib, Pillow, rasterio, pyproj, astroquery and Astropy.

*Use of AI*
- Claude (Anthropic) assisted with code drafting, debugging and explanations. All results were generated by this
  code from the data above and checked against independent references.

This is an independent student project for the NASA Space Apps Challenge 2026. It uses no NASA logos and is not
endorsed by NASA.
""")