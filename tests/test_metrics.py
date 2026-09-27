"""Sanity checks on src/metrics.py."""

import pandas as pd
import pytest

from src.metrics import (
    DEAL_BUCKET_LABELS,
    add_deal_labels,
    add_seat_type,
    daily_new_events,
    deal_quality_by_marketplace,
    deal_quality_distribution,
    delivery_type_mix,
    has_assigned_seats,
    marketplace_mix,
    marketplace_quality_coverage,
    overview_counts,
    seat_type_share,
)

MIX_FUNCS = [deal_quality_distribution, marketplace_mix, delivery_type_mix, seat_type_share]


def test_deal_bucket_values_are_in_0_7(listings):
    assert listings["dealBucket"].min() >= 0
    assert listings["dealBucket"].max() <= 7
    assert set(listings["dealBucket"].unique()) <= set(DEAL_BUCKET_LABELS)


def test_deal_labels_cover_every_row_and_every_bucket(listings):
    labeled = add_deal_labels(listings)
    assert labeled["dealBucketLabel"].isna().sum() == 0
    assert set(labeled["dealBucketLabel"].cat.categories) == set(DEAL_BUCKET_LABELS.values())
    # isQualityTier agrees with the bucket cutoff
    assert (labeled["isQualityTier"] == (labeled["dealBucket"] <= 3)).all()


def test_seat_type_partitions_all_rows(listings):
    has_seats = has_assigned_seats(listings)
    out = add_seat_type(listings)
    assert has_seats.isna().sum() == 0
    assert (out["seatType"] == "Assigned seats").sum() == has_seats.sum()
    assert (out["seatType"] == "GA / unassigned").sum() == (~has_seats).sum()


@pytest.mark.parametrize("func", MIX_FUNCS)
def test_mix_shares_sum_to_one_and_counts_match(listings, func):
    out = func(listings)
    assert out["share"].sum() == pytest.approx(1.0, abs=1e-9)
    assert out["count"].sum() == len(listings)
    assert (out["count"] > 0).all()


def test_deal_quality_by_marketplace_shares_sum_to_one_per_marketplace(listings):
    out = deal_quality_by_marketplace(listings)
    per_marketplace = out.groupby("marketplace")["share"].sum()
    assert (per_marketplace.round(9) == 1.0).all()


def test_marketplace_quality_coverage_share_is_bounded_and_consistent(listings):
    cov = marketplace_quality_coverage(listings)
    assert ((cov["quality_tier_share"] >= 0) & (cov["quality_tier_share"] <= 1)).all()
    assert (cov["n_quality_tier"] <= cov["n_listings"]).all()
    assert cov["n_listings"].sum() == len(listings)


def test_overview_counts_matches_table_lengths(tables, listings):
    counts = overview_counts(tables["events"], tables["performers"], tables["venues"], listings)
    assert counts == {
        "events": len(tables["events"]),
        "performers": len(tables["performers"]),
        "venues": len(tables["venues"]),
        "listings": len(listings),
    }


def test_daily_new_events_has_one_row_per_day_with_no_gaps(tables):
    out = daily_new_events(tables["events"])
    expected_days = pd.date_range(out["day"].min(), out["day"].max(), freq="D")
    assert list(out["day"]) == list(expected_days)
    assert out["newEvents"].sum() == len(tables["events"])
    assert (out["newEvents"] >= 0).all()
    assert (out["hitExportCap"] == (out["newEvents"] >= 1000)).all()
