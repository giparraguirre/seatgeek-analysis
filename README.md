# SeatGeek Analysis

## Data

The data is the free preview sample of the [SeatGeek dataset](https://rebrowser.net/products/datasets/seatgeek) published by Rebrowser. The full field reference, distributions and license terms are in [data/raw/DATASET_README.md](data/raw/DATASET_README.md).

The raw data files (parquet/csv) in `data/raw/` are git-ignored; that reference file and each table's `schema.json` are tracked. To reproduce, download the dataset from Rebrowser ([GitHub](https://github.com/rebrowser/seatgeek-dataset), [HuggingFace](https://huggingface.co/datasets/rebrowser/seatgeek-dataset) or [Zenodo](https://doi.org/10.5281/zenodo.18854665)) into `data/raw/`.

| Table | Folder | Layout | Raw rows (before dedup) |
| --- | --- | --- | --- |
| Events | `events/` | one file per day, last 30 days | 1,733 |
| Event listings | `event-listings/` | one file per day, up to 1,000 rows each, last 30 days | 30,000 |
| Performers | `performers/` | single file | 257 |
| Venues | `venues/` | single file | 193 |

Things to know:

- **Sample, not the full dataset.** Listings are 0.03% of the 98.7M full records, and their category shares differ a lot from the full-dataset figures on the Rebrowser page. Here `sg_app` delivery is 6.5% (19.0% in the full dataset), `electronic` is 93.5% (80.8%), `exchange` is 93.2% (97.3%), and listings with assigned seats are 15.1% (23% fill rate). This is not a code error: the seats counts match when read directly from the parquet and CSV files, and the daily shares swing widely (assigned seats range from 0.9% to 100% per day), most likely because each day's 1,000 listings come from a small set of events (555 distinct events across 30 days). Do not compare dashboard percentages to the full-dataset baseline.
- **Most listings do not join to an event.** Only 32 of the 555 distinct `eventId`s in listings appear in the events table, which is 4,000 of 30,000 listings (13%). The other 523 `eventId`s (26,000 listings) have no event row, so no type, venue or performer. This is inferred from the data patterns, not confirmed:
  - **Truncated export day.** 1,000 events were first seen on 2026-08-31, exactly the "up to 1,000 rows per day" cap, while every other day has 162 or fewer. 377 of the unmatched `eventId`s form one contiguous block (18376000-18379100) with zero events in the table, which fits rows cut off by that cap. More days would not recover them.
  - **Events older than the window.** Only the last 30 days are retained (2026-08-13 to 2026-09-11), so events first seen earlier are missing. Unmatched IDs such as 17565118 fit this case.
  - **The match is all-or-nothing by day.** On 26 of 30 days no listing matches an event; on the other 4, every listing does.

  Any analysis that needs event context (type, venue, performer) should use only the 4,000 matched listings. All 32 matched events are NBA games with exactly two performers, so event-level results cannot compare sports. Listing-only analysis (`dealBucket`, `marketplace`, `deliveryType`, section, quantity) can use all 30,000.
- **Premium fields are masked.** Columns marked 🔒 (listing `price`, `priceWithFees`, `fee`, `dealScore`; event price and count fields; performer image URLs) contain only `[PREMIUM]`. `src/clean.py` drops them. Deal quality comes from `dealBucket` instead.

### License and citation

Free for research and non-commercial use with attribution. Cite as: Rebrowser, *SeatGeek Events & Ticket Listings Dataset*, 2026, https://rebrowser.net/products/datasets/seatgeek. See the [license terms](https://rebrowser.net/free-datasets-for-research#license).
