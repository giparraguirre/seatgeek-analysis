"""KPI logic on top of the tables built in join_tables.py.

Two listing-level rules that every metric should reuse:

- Seat type comes from the listing's own `seats` array, never from events.isGa.
  full_listings has no event join, so isGa does not exist there.
- dealBucket 0-3 are deal-quality tiers; 4-6 are price tiers and 7 is "Other".
  All eight get labels and none are dropped, but "deal quality" charts should
  use isQualityTier so price tiers are not conflated with the quality story.
"""

import pandas as pd

DEAL_BUCKET_LABELS = {
    0: "Amazing",
    1: "Great",
    2: "Good",
    3: "Okay",
    4: "Price Tier A",
    5: "Price Tier B",
    6: "Price Tier C",
    7: "Other",
}
QUALITY_BUCKETS = [0, 1, 2, 3]


def has_assigned_seats(listings: pd.DataFrame) -> pd.Series:
    """True where specific seat numbers are listed; False for GA/unassigned.

    Works on full_listings (all rows) because it uses only the seats array.
    In this sample GA/unassigned rows are empty arrays, never null (0 nulls,
    25,462 empty, 4,538 non-empty); the notna() guard covers other data.
    """
    return listings["seats"].notna() & (listings["seats"].str.len() > 0)


def add_seat_type(listings: pd.DataFrame) -> pd.DataFrame:
    out = listings.copy()
    out["seatType"] = has_assigned_seats(out).map(
        {True: "Assigned seats", False: "GA / unassigned"}
    )
    return out


def add_deal_labels(listings: pd.DataFrame) -> pd.DataFrame:
    """Add dealBucketLabel (ordered, all 8 buckets) and isQualityTier (0-3)."""
    out = listings.copy()
    labels = pd.CategoricalDtype(list(DEAL_BUCKET_LABELS.values()), ordered=True)
    out["dealBucketLabel"] = out["dealBucket"].map(DEAL_BUCKET_LABELS).astype(labels)
    out["isQualityTier"] = out["dealBucket"].isin(QUALITY_BUCKETS)
    return out


def _share(count: pd.Series) -> pd.Series:
    """count / count.sum(), without dividing by zero on an empty input."""
    total = count.sum()
    return count / total if total else count.astype("float64")


def _mix(series: pd.Series, name: str) -> pd.DataFrame:
    """Counts and share of total for each value, most common first."""
    out = series.value_counts().rename_axis(name).reset_index(name="count")
    out["share"] = _share(out["count"])
    return out


def deal_quality_distribution(listings: pd.DataFrame) -> pd.DataFrame:
    """Listings per dealBucketLabel, in bucket order, all 8 buckets.

    isQualityTier separates the quality story (0-3) from price tiers and
    Other so charts can split or facet on it. share is of all listings.
    """
    df = add_deal_labels(listings)
    out = (
        df["dealBucketLabel"]
        .value_counts(sort=False)
        .rename_axis("dealBucketLabel")
        .reset_index(name="count")
    )
    quality = [DEAL_BUCKET_LABELS[b] for b in QUALITY_BUCKETS]
    out["isQualityTier"] = out["dealBucketLabel"].isin(quality)
    out["share"] = _share(out["count"])
    return out


def marketplace_mix(listings: pd.DataFrame) -> pd.DataFrame:
    return _mix(listings["marketplace"], "marketplace")


def delivery_type_mix(listings: pd.DataFrame) -> pd.DataFrame:
    return _mix(listings["deliveryType"], "deliveryType")


def seat_type_share(listings: pd.DataFrame) -> pd.DataFrame:
    return _mix(add_seat_type(listings)["seatType"], "seatType")


def deal_quality_by_marketplace(listings: pd.DataFrame) -> pd.DataFrame:
    """Quality-tier (0-3) mix within each marketplace.

    share is of that marketplace's quality-tier listings; n is that
    denominator, so tiny marketplaces (fan_to_fan has 1 listing) are visible
    as unreliable rather than looking like a 100% result.
    """
    df = add_deal_labels(listings)
    df = df[df["isQualityTier"]]
    out = (
        df.groupby(["marketplace", "dealBucketLabel"], observed=True)
        .size()
        .reset_index(name="count")
    )
    out["n"] = out.groupby("marketplace")["count"].transform("sum")
    out["share"] = _share(out["count"]) if out.empty else out["count"] / out["n"]
    return out


def marketplace_quality_coverage(listings: pd.DataFrame) -> pd.DataFrame:
    """How much of each marketplace is quality-tier (0-3) to begin with.

    Companion to deal_quality_by_marketplace: a marketplace can look great in
    that view while having few quality-tier listings at all.
    """
    df = add_deal_labels(listings)
    out = (
        df.groupby("marketplace")
        .agg(n_listings=("isQualityTier", "size"), n_quality_tier=("isQualityTier", "sum"))
        .reset_index()
        .sort_values("n_listings", ascending=False, ignore_index=True)
    )
    out["quality_tier_share"] = (
        out["n_quality_tier"] / out["n_listings"] if len(out) else out["n_listings"].astype("float64")
    )
    return out


def overview_counts(
    events: pd.DataFrame,
    performers: pd.DataFrame,
    venues: pd.DataFrame,
    listings: pd.DataFrame,
) -> dict[str, int]:
    """Simple row totals; needs none of the seat/deal-label preprocessing."""
    return {
        "events": len(events),
        "performers": len(performers),
        "venues": len(venues),
        "listings": len(listings),
    }


def daily_new_events(events: pd.DataFrame) -> pd.DataFrame:
    """New events per day (by _firstSeenAt), one row per day in the window,
    including days with zero. hitExportCap flags days at the 1,000-row/day
    export cap, where the true count of new events is likely higher.

    Aug 31 is the day traced during the listings-to-events join investigation
    (README's "Most listings do not join to an event"): it hits the cap, and
    a contiguous block of eventIds from that period has no matching event row.
    """
    day = events["_firstSeenAt"].dt.floor("D")
    full_range = pd.date_range(day.min(), day.max(), freq="D")
    counts = (
        day.value_counts()
        .reindex(full_range, fill_value=0)
        .rename_axis("day")
        .reset_index(name="newEvents")
    )
    counts["hitExportCap"] = counts["newEvents"] >= 1000
    return counts
