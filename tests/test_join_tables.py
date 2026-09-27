"""Sanity checks on src/join_tables.py."""


def test_full_listings_keeps_every_listing(joined, tables):
    assert len(joined["full_listings"]) == len(tables["event_listings"])


def test_matched_listings_is_a_subset_with_no_new_rows(joined, tables):
    """The inner join can only drop rows, never add them, and every eventId
    it keeps must exist in the events table."""
    matched = joined["matched_listings"]
    assert len(matched) <= len(tables["event_listings"])
    assert matched["listingId"].is_unique
    assert matched["eventId"].isin(tables["events"]["eventId"]).all()


def test_matched_listings_has_venue_columns_with_no_gaps(joined):
    """Every matched event's venue was found (events.venueId always resolves)."""
    venue_cols = [c for c in joined["matched_listings"].columns if c.startswith("venue_")]
    assert venue_cols, "expected venue_* columns from the venues join"
    assert joined["matched_listings"][venue_cols].isna().sum().sum() == 0


def test_event_performers_covers_every_event(joined, tables):
    ep = joined["event_performers"]
    assert set(ep["eventId"]) == set(tables["events"]["eventId"])
    assert not ep.duplicated().any()
    assert ep["performerId"].isin(tables["performers"]["performerId"]).all()


def test_listing_performers_credits_every_performer_of_a_listing(joined):
    """A listing with N performers on its event should produce N rows."""
    lp = joined["listing_performers"]
    ep = joined["event_performers"]
    matched = joined["matched_listings"]

    n_performers = ep.groupby("eventId").size().rename("n_performers")
    expected = (
        matched[["listingId", "eventId"]]
        .merge(n_performers, on="eventId")["n_performers"]
        .sum()
    )
    assert len(lp) == expected
    assert lp["listingId"].isin(matched["listingId"]).all()
