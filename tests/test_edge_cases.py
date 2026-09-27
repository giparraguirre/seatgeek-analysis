"""Edge cases the real data never exercises: synthetic inputs and empty inputs.

These sit apart from test_clean.py / test_join_tables.py / test_metrics.py
(which run against the real, cleaned data) because each one needs a
hand-built DataFrame to trigger a shape the real dataset doesn't have.
"""

import numpy as np
import pandas as pd
import pytest

from src.clean import drop_premium_columns
from src.join_tables import build_event_performers, build_matched_listings
from src.load_data import _read_daily_snapshots
from src.metrics import (
    deal_quality_by_marketplace,
    deal_quality_distribution,
    delivery_type_mix,
    marketplace_mix,
    marketplace_quality_coverage,
    seat_type_share,
)

MIX_FUNCS = [deal_quality_distribution, marketplace_mix, delivery_type_mix, seat_type_share]


# --- clean.py: array (object-dtype) columns must not crash the premium check ---


def test_drop_premium_columns_ignores_array_columns():
    """performerIds/seats are numpy arrays in an object column; comparing an
    array to a string raised `ValueError: truth value of an array is
    ambiguous` before _is_text() excluded object dtype. Regression guard."""
    df = pd.DataFrame(
        {
            "maskedText": ["[PREMIUM]", "[PREMIUM]"],
            "realText": ["a", "b"],
            "arrayCol": [np.array([1, 2]), np.array([])],
        }
    )
    out = drop_premium_columns(df)
    assert list(out.columns) == ["realText", "arrayCol"]


# --- join_tables.py: an event with zero performers ---


def test_event_with_no_performers_is_absent_from_event_performers():
    """explode() on an empty array drops the row entirely, so an event with
    zero performers silently has no row in event_performers. No event in the
    real data hits this today (see README), but the behavior should stay
    intentional, not accidental, if one ever does."""
    events = pd.DataFrame(
        {"eventId": [1, 2], "performerIds": [np.array([10, 20]), np.array([])]}
    )
    out = build_event_performers(events)
    assert set(out["eventId"]) == {1}  # event 2 has no row at all
    assert len(out) == 2


def test_matched_listings_raises_on_duplicate_venue_id():
    """validate="many_to_one" should catch a broken venues table (a duplicated
    venueId) instead of silently duplicating listing rows. This never fires
    on the real, deduped data, so it needs its own synthetic case."""
    listings = pd.DataFrame({"eventId": [1], "listingId": ["a"]})
    events = pd.DataFrame(
        {
            "eventId": [1],
            "venueId": [100],
            "performerIds": [np.array([])],
            "_primaryKey": ["p"],
            "_firstSeenAt": [pd.Timestamp.now()],
            "_lastSeenAt": [pd.Timestamp.now()],
        }
    )
    venues = pd.DataFrame(
        {
            "venueId": [100, 100],  # duplicated key
            "name": ["Arena A", "Arena A dup"],
            "_primaryKey": ["v1", "v2"],
            "_firstSeenAt": [pd.Timestamp.now()] * 2,
            "_lastSeenAt": [pd.Timestamp.now()] * 2,
        }
    )
    with pytest.raises(pd.errors.MergeError):
        build_matched_listings(listings, events, venues)


# --- metrics.py: empty input should not divide by zero ---


@pytest.mark.parametrize("func", MIX_FUNCS)
def test_mix_functions_on_empty_listings_return_zero_not_nan(func):
    """0/0 should give 0.0 shares (or an empty table), never NaN."""
    empty = pd.DataFrame(
        columns=["marketplace", "deliveryType", "dealBucket", "seats"]
    ).astype({"dealBucket": "float64"})
    empty["seats"] = pd.Series([], dtype=object)
    out = func(empty)
    assert not out["share"].isna().any()
    if func is deal_quality_distribution:
        # dealBucketLabel is categorical, so value_counts reports every
        # bucket at count 0 rather than an empty table - both are fine,
        # as long as neither divides by zero into NaN.
        assert len(out) == 8
        assert (out["count"] == 0).all()
        assert (out["share"] == 0.0).all()
    else:
        assert len(out) == 0


def test_marketplace_quality_coverage_on_empty_listings():
    empty = pd.DataFrame(columns=["marketplace", "dealBucket"]).astype(
        {"dealBucket": "float64"}
    )
    out = marketplace_quality_coverage(empty)
    assert len(out) == 0
    assert not out["quality_tier_share"].isna().any()


def test_deal_quality_by_marketplace_on_empty_listings():
    empty = pd.DataFrame(columns=["marketplace", "dealBucket"]).astype(
        {"dealBucket": "float64"}
    )
    out = deal_quality_by_marketplace(empty)
    assert len(out) == 0
    assert not out["share"].isna().any()


# --- load_data.py: missing raw data should raise a clear, actionable error ---


def test_read_daily_snapshots_raises_clear_error_when_dir_is_empty(tmp_path):
    (tmp_path / "data").mkdir()  # exists, but no parquet files in it
    with pytest.raises(FileNotFoundError, match="data/raw"):
        _read_daily_snapshots(tmp_path)


def test_read_daily_snapshots_raises_clear_error_when_dir_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="data/raw"):
        _read_daily_snapshots(tmp_path / "does_not_exist")
