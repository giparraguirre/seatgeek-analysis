"""Sanity checks on src/clean.py."""

import pandas as pd

from src.clean import PREMIUM_TOKEN, find_premium_columns


def test_no_premium_token_survives(tables):
    """[PREMIUM] should not appear anywhere after cleaning."""
    for name, df in tables.items():
        text_cols = df.select_dtypes(include="string").columns
        for c in text_cols:
            assert not (df[c] == PREMIUM_TOKEN).any(), f"{name}.{c} still has {PREMIUM_TOKEN}"


def test_premium_columns_are_gone(tables, raw_tables):
    """Columns that were 100% [PREMIUM] in the raw table are dropped."""
    for name, df in tables.items():
        dropped = find_premium_columns(raw_tables[name])
        assert not set(dropped) & set(df.columns)


def test_id_columns_are_nullable_int(tables):
    for col in ("eventId", "venueId"):
        assert tables["events"][col].dtype == "Int64"
    assert tables["event_listings"]["eventId"].dtype == "Int64"
    assert tables["performers"]["performerId"].dtype == "Int64"
    assert tables["venues"]["venueId"].dtype == "Int64"


def test_dedupe_keys_are_unique(tables):
    assert tables["events"]["eventId"].is_unique
    assert tables["event_listings"]["listingId"].is_unique
    assert tables["performers"]["performerId"].is_unique
    assert tables["venues"]["venueId"].is_unique


def test_dedupe_does_not_drop_more_than_duplicates(tables, raw_tables):
    """Row count only drops by the number of duplicate keys, nothing else."""
    # eventId/performerId/venueId are numeric-as-string in the raw tables;
    # listingId is already an opaque string, so it needs no numeric coercion.
    numeric_key = {"events": "eventId", "performers": "performerId", "venues": "venueId"}
    for name, col in numeric_key.items():
        raw = raw_tables[name]
        n_dupes = pd.to_numeric(raw[col], errors="coerce").duplicated().sum()
        assert len(tables[name]) == len(raw) - n_dupes

    raw = raw_tables["event_listings"]
    n_dupes = raw["listingId"].duplicated().sum()
    assert len(tables["event_listings"]) == len(raw) - n_dupes


def test_venue_capacity_zero_becomes_na(tables, raw_tables):
    raw_zeros = (raw_tables["venues"]["capacity"] == 0).sum()
    assert tables["venues"]["capacity"].isna().sum() == raw_zeros
    assert (tables["venues"]["capacity"].dropna() > 0).all()
