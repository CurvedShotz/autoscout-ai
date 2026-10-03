# AutoScout AI

AutoScout AI is an AI-powered used-car search and evaluation assistant. Users describe the kind of vehicle they want in natural language, and the system converts that intent into structured search criteria, retrieves live listings, ranks them based on user fit, and independently evaluates each listing for potential anomaly or scam-like risk.

The current live listing provider is Auto.dev, with the architecture designed so additional marketplace or listing providers can be added later.

## High-Level Goals

- **Natural Language Discovery**: Let users describe what they want in plain English, such as *“Reliable commuter under $15k with low mileage near Chicago.”*
- **Live Vehicle Search**: Retrieve real vehicle listings through supported listing providers.
- **Provider-Neutral Architecture**: Normalize external listing data into a consistent internal schema so the application is not tightly coupled to a single provider.
- **Intelligent Ranking**: Rank vehicles based on how well they match the user's request, including factors such as price, mileage, year, history, body style, and stated preferences.
- **Independent Risk Analysis**: Evaluate listing anomalies and suspicious characteristics separately from recommendation quality.
- **Scalable Monorepo Foundation**: Maintain clear separation between backend services, AI integrations, provider adapters, frontend components, and infrastructure.

---

## Features

### Natural-Language Search

Users can search with conversational requests such as:

```text
Find me a reliable Honda or Toyota around $15,000.
```

```text
Show me a sporty sedan under 60k miles.
```

```text
Find me a Toyota Camry near Dallas under $20k.
```

The backend converts these requests into structured intent while distinguishing between:

- hard filters such as maximum price, mileage, model year, and body style;
- alternative makes or models;
- approximate targets;
- softer preferences such as reliability or sportiness.

### Search Planning

A dedicated search-planning layer converts parsed user intent into one or more provider requests.

This allows the system to support queries containing alternatives while avoiding invalid combinations or unnecessary provider calls.

### Location-Aware Search

Searches can use either ZIP codes or natural-language locations such as:

```text
Dallas
Dallas, TX
Denton
Denton, TX
75001
```

Place names are resolved into provider-compatible geographic filters before vehicle retrieval.

Direct ZIP searches bypass geocoding.

### Live Listing Retrieval

AutoScout AI currently retrieves live listing data from Auto.dev.

Provider responses are normalized into an internal `VehicleListing` model containing fields such as:

- VIN
- year, make, model, and trim
- price and mileage
- body style and drivetrain
- engine and transmission
- dealer and location
- accident and ownership history
- listing and vehicle-history URLs

### AI Ranking

Listings are ranked according to how well they satisfy the user's request.

The ranking layer considers factors such as:

- budget fit
- mileage
- model year
- ownership and accident history
- user preferences
- approximate price and mileage targets
- body style and general vehicle desirability

The ranking system is provider-neutral and currently uses Gemini as the default AI provider.

### Independent Listing Risk Analysis

Each listing is evaluated separately for potential anomaly or scam-like risk.

The risk analyzer produces:

- a risk score from 0–100;
- a low, medium, or high risk level;
- supporting signals;
- a short explanation.

Ranking and risk are intentionally separate concepts.

A vehicle can be a poor match for the user while still being a legitimate-looking listing, and a highly relevant vehicle can still contain suspicious listing characteristics.

### Safe Empty Results

Restrictive searches that return no vehicles are treated as valid searches.

Instead of surfacing an upstream error, the API returns:

```json
{
  "data": []
}
```

Ranking and risk analysis are skipped when no listings are available.

---

## Architecture

The current natural-language search flow is:

```text
User Query
    |
    v
Natural-Language Intent Parser
    |
    v
UserSearchIntent
    |
    v
Search Planner
    |
    v
Location Resolution
(if required)
    |
    v
Auto.dev Listing Retrieval
    |
    v
Provider-Neutral Normalization
    |
    v
Merge + VIN Deduplication
    |
    +-------------------+
    |                   |
    v                   v
AI Ranking        Risk Analysis
    |                   |
    +---------+---------+
              |
              v
      VIN-Based Combiner
              |
              v
        FastAPI Response
              |
              v
        Next.js Frontend
```

The architecture keeps major responsibilities isolated:

- parsing understands what the user means;
- search planning decides how to retrieve listings;
- provider adapters handle external APIs;
- normalization removes provider-specific response shapes;
- ranking evaluates user fit;
- risk analysis evaluates listing anomalies;
- the frontend displays the combined result without duplicating backend business logic.

---

## Tech Stack

### Backend

- Python 3.13
- FastAPI
- Pydantic
- pydantic-settings
- httpx
- pytest
- uv

### AI

- Google Gemini through the `google-genai` SDK
- provider-neutral ranking and parsing interfaces
- OpenAI adapter retained for alternative provider support

### Vehicle Data

- Auto.dev vehicle listings API
- ZIP + distance geographic filtering
- OpenStreetMap / Nominatim-based location resolution for place-name searches

### Frontend

- Next.js
- React
- TypeScript
- custom responsive CSS

### Project Structure

```text
apps/
  api/        FastAPI backend
  web/        Next.js frontend

packages/     Shared or reusable project packages
docs/         Project documentation
infrastructure/
scripts/
```

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for project milestones and planned development phases.

Areas still under active development include:

- broader vehicle-provider support;
- improved geographic search behavior;
- richer frontend search and comparison experiences;
- additional ranking and risk calibration;
- search quality evaluation and provider coverage testing.

---

## Getting Started

### Backend

Navigate to the API application:

```bash
cd apps/api
```

Install dependencies:

```bash
uv sync
```

Create your environment file from the example configuration and add the required API credentials.

Then start the backend:

```bash
uv run uvicorn app.main:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### Frontend

Open a second terminal:

```bash
cd apps/web
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:3000
```

The frontend uses:

```text
NEXT_PUBLIC_API_BASE_URL
```

to configure the backend API address and falls back to the local FastAPI server during development.

---

## Testing

Run the backend test suite from `apps/api`:

```bash
uv run pytest
```

The backend includes tests for:

- provider requests;
- listing normalization;
- natural-language parsing;
- search planning;
- location resolution;
- ranking validation;
- risk-analysis validation;
- structured search;
- natural-language search;
- empty-result handling;
- upstream error behavior.

Frontend validation can be run with:

```bash
npm run lint
npm run typecheck
```

---

## Current Limitations

AutoScout AI is still under active development.

Current limitations include:

- vehicle availability depends on the inventory exposed by the current listing provider;
- restrictive geographic or pricing filters may legitimately return zero results;
- geographic resolution currently relies on public geocoding infrastructure that may not be suitable for high-volume production traffic;
- marketplace coverage is currently limited compared with the long-term multi-provider goal;
- AI ranking and risk analysis are decision-support tools rather than guarantees of vehicle quality, legitimacy, or condition.
