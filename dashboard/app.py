"""SeatGeek listings dashboard. Run from the project root:

    streamlit run dashboard/app.py

Presentation only: every number comes from src/metrics.py. Judgment calls that
belong to the UI (like greying out groups with fewer than MIN_N listings) live
here, so the metric functions stay complete.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.clean import clean_all
from src.join_tables import build_all
from src.load_data import load_all
from src.metrics import (
    DEAL_BUCKET_LABELS,
    QUALITY_BUCKETS,
    daily_new_events,
    deal_quality_by_marketplace,
    deal_quality_distribution,
    delivery_type_mix,
    marketplace_mix,
    marketplace_quality_coverage,
    overview_counts,
    seat_type_share,
)

MIN_N = 30  # groups smaller than this are shown gray and footnoted, not dropped
QUALITY_LABELS = [DEAL_BUCKET_LABELS[b] for b in QUALITY_BUCKETS]

# Colors that read on both light and dark pages (validated with
# validate_palette.js --ordinal in both modes). Text, gridlines and axes are left
# to Streamlit's own chart theme, so the charts follow the page theme even when
# the viewer switches it mid-session.
RAMP = ["#1c5cab", "#2a78d6", "#5598e7", "#86b6ef"]  # Amazing -> Okay, one blue hue
RAMP_TEXT = ["#ffffff", "#ffffff", "#0b0b0b", "#0b0b0b"]  # label ink on each step
ACCENT = "#2a78d6"
GRAY = "#898781"  # price tiers, Other, and groups with too few listings


@st.cache_data(show_spinner="Loading and cleaning data...")
def load_tables():
    tables = clean_all(load_all())
    return tables, build_all(tables)


def style(fig: go.Figure, height: int, xtitle: str | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=10, t=10, b=0),
        font=dict(size=13),
        bargap=0.45,
        hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(
        zeroline=False, showline=False, title=xtitle,
        tickformat=".0%", rangemode="tozero",
    )
    fig.update_yaxes(autorange="reversed", showgrid=False, showline=False, ticks="")
    return fig


def bar_label(share: float, count: int) -> str:
    """Percent label; tiny shares also show the raw count so they are not just 0.0%."""
    if share >= 0.01:
        return f"{share:.1%}"
    if share < 0.0001:
        return f"<0.01% ({count:,})"
    return f"{share:.2%} ({count:,})"


def bar_chart(df, cat, height, colors=None, xtitle="Share of listings"):
    """Horizontal bars of df['share'] with the share printed at the bar end."""
    fig = go.Figure(
        go.Bar(
            x=df["share"], y=df[cat].astype(str), orientation="h",
            marker=dict(color=colors or ACCENT, cornerradius=4),
            text=[bar_label(s, c) for s, c in zip(df["share"], df["count"])],
            textposition="outside", cliponaxis=False,
            customdata=df[["count"]],
            hovertemplate="%{y}<br>%{customdata[0]:,} listings (%{x:.1%})<extra></extra>",
        )
    )
    style(fig, height, xtitle)
    upper = df["share"].max() * 1.35
    fig.update_xaxes(range=[0, upper])
    if upper > 1:  # leave room for the end label, but do not tick past 100%
        fig.update_xaxes(tickvals=[0, 0.2, 0.4, 0.6, 0.8, 1.0])
    return fig


def show(fig, data: pd.DataFrame):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with st.expander("Show data"):
        st.dataframe(data, hide_index=True, width="stretch")


st.set_page_config(page_title="SeatGeek Listings", layout="wide")
st.title("SeatGeek listings")

try:
    tables, joined = load_tables()
except FileNotFoundError:
    st.error(
        "Raw data not found in data/raw/. Download the dataset (see the README's "
        "Data section) and reload."
    )
    st.stop()

listings = joined["full_listings"]

# --- Overview -----------------------------------------------------------------
counts = overview_counts(
    tables["events"], tables["performers"], tables["venues"], listings
)
cols = st.columns(4)
for col, (label, value) in zip(cols, counts.items()):
    col.metric(label.capitalize(), f"{value:,}")
matched = len(joined["matched_listings"])
st.caption(
    f"Only {matched:,} of {len(listings):,} listings ({matched / len(listings):.0%}) "
    "match an events row, and all of those are NBA games. Every panel below uses "
    "listing-only columns, so it covers all listings."
)

# --- Daily new events ----------------------------------------------------------
st.header("New events per day")
dv = daily_new_events(tables["events"])
cap_day = dv.loc[dv["hitExportCap"], "day"]
zero_days = dv.loc[dv["newEvents"] == 0, "day"]
fig = go.Figure(
    go.Scatter(
        x=dv["day"], y=dv["newEvents"], mode="lines+markers",
        line=dict(color=ACCENT, width=2), marker=dict(size=6, color=ACCENT),
        hovertemplate="%{x|%b %-d}: %{y:,} new events<extra></extra>",
        showlegend=False,
    )
)
if len(cap_day):
    fig.add_trace(
        go.Scatter(
            x=cap_day, y=dv.loc[dv["hitExportCap"], "newEvents"], mode="markers",
            marker=dict(size=12, color=GRAY, symbol="circle-open", line=dict(width=2)),
            hovertemplate="%{x|%b %-d}: hit the 1,000/day export cap<br>"
            "(true new-event count is likely higher)<extra></extra>",
            showlegend=False,
        )
    )
    fig.add_annotation(
        x=cap_day.iloc[0], y=1000, text="Hit the export cap", showarrow=True,
        arrowhead=0, ax=45, ay=-15, font=dict(size=12, color=GRAY),
    )
for zd in zero_days:
    fig.add_vline(x=zd, line=dict(color=GRAY, width=1, dash="dot"))
style(fig, 280, "First-seen date")
fig.update_xaxes(tickformat="%b %-d", dtick=7 * 24 * 60 * 60 * 1000)
fig.update_yaxes(autorange=True, rangemode="tozero")
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with st.expander("Show data"):
    st.dataframe(dv, hide_index=True, width="stretch")
st.caption(
    "Aug 31 hits the daily export cap of 1,000 rows, so its true count of new "
    "events is likely higher; a block of eventIds from around that day has no "
    "matching event row (see the README's join-rate note). Dotted lines mark "
    "days with zero new events (Aug 17-18)."
)

# --- Deal quality -------------------------------------------------------------
st.header("Deal quality")
dq = deal_quality_distribution(listings)
dq_colors = [
    RAMP[QUALITY_LABELS.index(lbl)] if q else GRAY
    for lbl, q in zip(dq["dealBucketLabel"], dq["isQualityTier"])
]
show(bar_chart(dq, "dealBucketLabel", 340, dq_colors), dq)
st.caption(
    "Blue bars are deal-quality tiers (Amazing to Okay). Gray bars are price tiers "
    "and Other, which are not a quality rating."
)

# --- Marketplace mix ----------------------------------------------------------
st.header("Marketplace mix")
mm = marketplace_mix(listings)
show(bar_chart(mm, "marketplace", 260), mm)

# --- Delivery & seat type -----------------------------------------------------
st.header("Delivery and seat type")
left, right = st.columns(2)
with left:
    st.subheader("Delivery type")
    dm = delivery_type_mix(listings)
    show(bar_chart(dm, "deliveryType", 220), dm)
with right:
    st.subheader("Seat type")
    ss = seat_type_share(listings)
    show(bar_chart(ss, "seatType", 220), ss)

# --- Cross-cuts ---------------------------------------------------------------
st.header("Deal quality by marketplace")
cov = marketplace_quality_coverage(listings)
by_mp = deal_quality_by_marketplace(listings)
order = cov["marketplace"].tolist()  # most listings first, shared by both charts
n_listings = cov.set_index("marketplace")["n_listings"]
small = {m: n_listings[m] < MIN_N for m in order}


def mp_label(m: str) -> str:
    return f"{m} (n={n_listings[m]:,}){'†' if small[m] else ''}"


labels = [mp_label(m) for m in order]
left, right = st.columns(2)

with left:
    st.subheader("Mix of quality tiers")
    fig = go.Figure()
    for i, tier in enumerate(QUALITY_LABELS):
        rows = by_mp[by_mp["dealBucketLabel"] == tier].set_index("marketplace")
        share = [rows["share"].get(m, 0.0) for m in order]
        count = [int(rows["count"].get(m, 0)) for m in order]
        fig.add_trace(
            go.Bar(
                name=tier, x=share, y=labels, orientation="h",
                marker=dict(
                    color=[GRAY if small[m] else RAMP[i] for m in order],
                    line=dict(color="rgba(255,255,255,0.55)", width=1.5),
                ),
                # small groups are gray, so the tier name goes in the bar
                text=[
                    (f"{s:.0%} {tier}" if s >= 0.15 else "")
                    if small[m]
                    else (f"{s:.0%}" if s >= 0.08 else "")
                    for s, m in zip(share, order)
                ],
                textposition="inside", insidetextanchor="middle", textangle=0,
                textfont=dict(
                    color=["#0b0b0b" if small[m] else RAMP_TEXT[i] for m in order]
                ),
                customdata=count,
                hovertemplate=f"{tier}<br>%{{customdata:,}} listings (%{{x:.1%}} of "
                "the marketplace's quality-tier listings)<extra></extra>",
            )
        )
    style(fig, 300, "Share of the marketplace's quality-tier listings")
    fig.update_layout(
        barmode="stack",
        legend=dict(orientation="h", y=-0.3, x=0, traceorder="normal"),
    )
    fig.update_xaxes(range=[0, 1])
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with st.expander("Show data"):
        st.dataframe(by_mp, hide_index=True, width="stretch")

with right:
    st.subheader("Quality-tier share of all listings")
    fig = go.Figure(
        go.Bar(
            x=cov["quality_tier_share"], y=labels, orientation="h",
            marker=dict(
                color=[GRAY if small[m] else ACCENT for m in order],
                cornerradius=4,
            ),
            text=[f"{s:.0%}" for s in cov["quality_tier_share"]],
            textposition="outside", cliponaxis=False,
            customdata=cov[["n_quality_tier", "n_listings"]],
            hovertemplate="%{y}<br>%{customdata[0]:,} of %{customdata[1]:,} "
            "listings are quality-tier (%{x:.1%})<extra></extra>",
        )
    )
    style(fig, 300, "Quality-tier listings as a share of the marketplace")
    fig.update_xaxes(range=[0, 1.15], tickvals=[0, 0.25, 0.5, 0.75, 1])
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with st.expander("Show data"):
        st.dataframe(cov, hide_index=True, width="stretch")

st.caption(
    f"† Fewer than {MIN_N} listings: shown in gray because a share from so few "
    "listings is not reliable; a gray bar names its tier in the bar. "
    "In the left chart, segments under 8% have no label; hover any segment for "
    "its count and share."
)
