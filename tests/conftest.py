"""Shared fixtures. Load, clean, and join the real data once per test run."""

import pytest

from src.clean import clean_all
from src.join_tables import build_all
from src.load_data import load_all


@pytest.fixture(scope="session")
def raw_tables():
    return load_all()


@pytest.fixture(scope="session")
def tables(raw_tables):
    """Cleaned events, event_listings, performers, venues."""
    return clean_all(raw_tables)


@pytest.fixture(scope="session")
def joined(tables):
    """full_listings, matched_listings, event_performers, listing_performers."""
    return build_all(tables)


@pytest.fixture(scope="session")
def listings(joined):
    return joined["full_listings"]
