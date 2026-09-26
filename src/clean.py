"""Clean the raw SeatGeek tables: masked columns, dtypes, nulls, duplicates."""

import pandas as pd

PREMIUM_TOKEN = "[PREMIUM]"
NULL_TOKENS = ["", "N/A", "null", "None", "nan", PREMIUM_TOKEN]

EVENT_ID_COLS = ["eventId", "venueId"]
LISTING_ID_COLS = ["eventId"]  # listingId is an opaque string, keep as-is
PERFORMER_ID_COLS = ["performerId", "homeVenueId"]
VENUE_ID_COLS = ["venueId", "metroCode"]


def find_premium_columns(df: pd.DataFrame) -> list[str]:
    """Columns where every value is the [PREMIUM] mask (no usable data)."""
    return [
        c
        for c in df.columns
        if _is_text(df[c]) and (df[c] == PREMIUM_TOKEN).all()
    ]


def _is_text(s: pd.Series) -> bool:
    # object columns hold arrays here (performerIds, seats), not strings
    return pd.api.types.is_string_dtype(s) and s.dtype != object


def drop_premium_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=find_premium_columns(df))


def _blank_strings_to_na(df: pd.DataFrame) -> pd.DataFrame:
    """Turn empty/placeholder strings (and stray [PREMIUM] values) into NA."""
    for c in df.columns:
        if _is_text(df[c]):
            df[c] = df[c].replace(NULL_TOKENS, pd.NA)
    return df


def _to_int_ids(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Cast ID columns (float / str / int depending on table) to nullable Int64."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    return df


def _dedupe_latest(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """One row per key, keeping the most recently seen record."""
    return (
        df.sort_values(["_lastSeenAt", "_firstSeenAt"])
        .drop_duplicates(subset=key, keep="last")
        .sort_index()
        .reset_index(drop=True)
    )


def clean_events(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_premium_columns(df.copy())
    df = _blank_strings_to_na(df)
    df = _to_int_ids(df, EVENT_ID_COLS)
    return _dedupe_latest(df, "eventId")


def clean_event_listings(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_premium_columns(df.copy())
    df = _blank_strings_to_na(df)
    df = _to_int_ids(df, LISTING_ID_COLS)
    return _dedupe_latest(df, "listingId")


def clean_performers(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_premium_columns(df.copy())
    df = _blank_strings_to_na(df)
    df = _to_int_ids(df, PERFORMER_ID_COLS)
    return _dedupe_latest(df, "performerId")


def clean_venues(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_premium_columns(df.copy())
    df = _blank_strings_to_na(df)
    df = _to_int_ids(df, VENUE_ID_COLS)
    # capacity of 0 is a missing value, not an empty venue
    df["capacity"] = df["capacity"].where(df["capacity"] > 0)
    return _dedupe_latest(df, "venueId")


def clean_all(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "events": clean_events(tables["events"]),
        "event_listings": clean_event_listings(tables["event_listings"]),
        "performers": clean_performers(tables["performers"]),
        "venues": clean_venues(tables["venues"]),
    }
