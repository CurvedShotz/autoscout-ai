# AutoScout AI API

This directory contains the backend foundation for AutoScout AI.

## Development

Create a virtual environment with uv:

```bash
uv venv .venv
```

Install dependencies:

```bash
uv sync
```

Run the development server:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API exposes a health endpoint at `/health`.

## Natural-language search

`POST /search/natural` accepts a JSON body with a non-empty `query` string. The API
parses the query, plans one or more Auto.dev searches, merges listings by VIN, and
ranks the result set with the configured AI ranking provider. Requested body styles
are used as Auto.dev retrieval filters. Soft preferences, target price, target
mileage, and make/model alternatives are passed to ranking separately from hard
retrieval filters.

City and place locations are resolved to a ZIP before listing retrieval. Auto.dev's
[Search Vehicle Listings API](https://docs.auto.dev/v2/reference/searchVehicleListings)
documents the geographic filters `zip` and `distance`; city/state and coordinate
filters are not used. Place searches use the resolved ZIP plus
`AUTO_DEV_SEARCH_DISTANCE_MILES` (default 50, configurable). Direct ZIP searches
continue to send only `zip`, preserving their existing provider behavior.

The default resolver uses OpenStreetMap Nominatim. Repeated results are cached in
process memory (up to 256 locations), and requests are throttled to no more than one
per second. Nominatim's public service is suitable only for modest, end-user-driven
volume; production deployments must be able to switch
`LOCATION_GEOCODER_BASE_URL` to another provider or self-hosted instance. Public
Nominatim requires application identification, attribution, and adherence to its
usage policy. The frontend displays OpenStreetMap attribution in the footer.

An exact ZIP is passed through without a geocoder request. Place names are matched
against geocoder results; a unique city/municipality is preferred over a town with
the same name. If multiple city-level places remain, the API rejects the location
instead of guessing. Unresolved or ambiguous places return HTTP 422; resolver
availability failures return a sanitized HTTP 502.

Natural searches are all-or-nothing across planned Auto.dev requests: if any
planned provider request fails, the API returns an upstream error instead of
ranking incomplete results.

## Manual listing risk analysis

Run `uv run python scripts/manual_listing_risk.py` from `apps/api` to fetch live
Toyota Camry listings, normalize them, and assess listing anomalies with Gemini.
This script is also useful for inspecting raw risk assessments without search ranking.

Search results now include an independent listing-risk assessment alongside the
ranking score and reason. Both endpoints require risk analysis to succeed for
non-empty results; a risk-provider failure returns a sanitized 502 instead of
silently omitting risk. Ranking scores are not changed by risk scores.

Run `uv run python scripts/manual_search_with_risk.py` from `apps/api` for a live
natural-search, ranking, and risk-analysis check.

Run `uv run python scripts/evaluate_listing_risk_calibration.py` from `apps/api`
to assess a controlled mixed listing set against broad scenario score bands and
qualitative consistency checks. The evaluation bands are diagnostic only and do
not change production risk scores.
