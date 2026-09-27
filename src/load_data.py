"""Read the raw SeatGeek tables from data/raw into DataFrames."""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def _read_daily_snapshots(table_dir: Path) -> pd.DataFrame:
    """Concatenate every daily parquet file in <table_dir>/data/."""
    files = sorted((table_dir / "data").glob("*.parquet"))
    if not files:
        raise FileNotFoundError(
            f"No daily parquet files found in {table_dir / 'data'}. "
            "Download the dataset into data/raw/ (see the README's Data section)."
        )
    return pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)


def load_events(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    return _read_daily_snapshots(raw_dir / "events")


def load_event_listings(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    return _read_daily_snapshots(raw_dir / "event-listings")


def load_performers(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    return pd.read_parquet(raw_dir / "performers" / "data.parquet")


def load_venues(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    return pd.read_parquet(raw_dir / "venues" / "data.parquet")


def load_all(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    return {
        "events": load_events(raw_dir),
        "event_listings": load_event_listings(raw_dir),
        "performers": load_performers(raw_dir),
        "venues": load_venues(raw_dir),
    }
