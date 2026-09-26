"""Build the analysis tables from the cleaned SeatGeek tables.

Four outputs, kept separate on purpose (only ~13% of listings have an events
row, so a left join would leave most rows empty for every event column):

- full_listings:      all listings, listing-only columns, no event join.
- matched_listings:   inner join listings -> events -> venues, one row per listing.
- event_performers:   one row per (event, performer) pair, built from all events.
- listing_performers: matched_listings x event_performers x performers, one row
                      per (listing, performer). Sum listings here, not in
                      matched_listings, to credit every performer of an event.
"""

from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

# Bookkeeping columns that exist on every raw table; keep only the listing's own.
_META_COLS = ["_primaryKey", "_firstSeenAt", "_lastSeenAt"]


def build_full_listings(listings: pd.DataFrame) -> pd.DataFrame:
    return listings.copy()


def build_event_performers(events: pd.DataFrame) -> pd.DataFrame:
    """Explode the performerIds array into one row per event-performer pair."""
    pairs = events[["eventId", "performerIds"]].explode("performerIds")
    pairs = pairs.rename(columns={"performerIds": "performerId"})
    pairs["performerId"] = pd.to_numeric(pairs["performerId"]).astype("Int64")
    return pairs.dropna(subset=["performerId"]).drop_duplicates().reset_index(drop=True)


def build_matched_listings(
    listings: pd.DataFrame, events: pd.DataFrame, venues: pd.DataFrame
) -> pd.DataFrame:
    """Inner join listings to their event, then the event's venue.

    Venue columns are prefixed with 'venue_' to avoid clashing with event
    columns (name, url, ...). performerIds is dropped; use event_performers.
    """
    events = events.drop(columns=_META_COLS + ["performerIds"])
    venues = venues.drop(columns=_META_COLS)
    venues = venues.rename(
        columns={c: f"venue_{c}" for c in venues.columns if c != "venueId"}
    )
    out = listings.merge(events, on="eventId", how="inner", validate="many_to_one")
    return out.merge(venues, on="venueId", how="left", validate="many_to_one")


def build_listing_performers(
    matched_listings: pd.DataFrame,
    event_performers: pd.DataFrame,
    performers: pd.DataFrame,
) -> pd.DataFrame:
    """One row per (listing, performer): an event's listings count toward each
    of its performers. Performer columns are prefixed with 'performer_'."""
    performers = performers.drop(columns=_META_COLS)
    performers = performers.rename(
        columns={c: f"performer_{c}" for c in performers.columns if c != "performerId"}
    )
    out = matched_listings.merge(
        event_performers, on="eventId", how="inner", validate="many_to_many"
    )
    return out.merge(performers, on="performerId", how="left", validate="many_to_one")


def build_all(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """tables: the dict returned by clean.clean_all()."""
    full_listings = build_full_listings(tables["event_listings"])
    matched_listings = build_matched_listings(
        tables["event_listings"], tables["events"], tables["venues"]
    )
    event_performers = build_event_performers(tables["events"])
    return {
        "full_listings": full_listings,
        "matched_listings": matched_listings,
        "event_performers": event_performers,
        "listing_performers": build_listing_performers(
            matched_listings, event_performers, tables["performers"]
        ),
    }


if __name__ == "__main__":
    # run from the project root: python -m src.join_tables
    from src.clean import clean_all
    from src.load_data import load_all

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in build_all(clean_all(load_all())).items():
        df.to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False)
        print(f"{name}: {df.shape}")
