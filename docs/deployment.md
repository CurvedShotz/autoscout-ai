# AutoScout deployment preparation

This document describes the deployment shape prepared for AutoScout. No AWS
resources are changed by the build commands below.

## Backend: AWS App Runner

Use an App Runner service sourced from an image in Amazon ECR. The repository is
a monorepo, and the API requires Python 3.13; the container pins the runtime and
installs the API's locked production dependencies without relying on App Runner's
managed Python runtime or a preinstalled `uv`.

Build from the repository root:

```bash
docker build -t autoscout-api:latest -f apps/api/Dockerfile apps/api
```

The Docker build runs `uv sync --locked --no-dev`. The container starts with:

```bash
/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
```

Configure the App Runner container port and `PORT` as `8080`. The service health
check path is `/health`; it makes no external provider calls. For local
development, run from `apps/api`:

```bash
uv sync --locked
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Set these App Runner environment variables:

| Variable | Required | Purpose |
| --- | --- | --- |
| `AUTO_DEV_API_KEY` | Yes | Server-side credential for Auto.dev listing requests |
| `GEMINI_API_KEY` | Yes | Query parsing, default Gemini ranking, and listing-risk analysis |
| `ENVIRONMENT` | Yes | Set to `production` |
| `DEBUG` | Yes | Set to `false` |
| `CORS_ORIGINS` | Yes | Exact comma-separated browser origins, normally `https://danielolowe.com` |
| `PORT` | Yes | Set to `8080`, matching the App Runner service port |
| `SEARCH_RATE_LIMIT_REQUESTS` | No | Per-client search count per window; default `10` |
| `SEARCH_RATE_LIMIT_WINDOW_SECONDS` | No | Search rate-limit window; default `60` |
| `AUTO_DEV_SEARCH_DISTANCE_MILES` | No | Place-search radius; default `50` |
| `LOCATION_GEOCODER_BASE_URL` | No | Nominatim-compatible service URL |
| `LOCATION_GEOCODER_USER_AGENT` | No | Geocoder application identification |
| `AI_RANKING_PROVIDER` | No | Defaults to `gemini`; use `openai` only with `OPENAI_API_KEY` |
| `OPENAI_API_KEY` | Conditional | Needed only when `AI_RANKING_PROVIDER=openai` |
| `GEMINI_RANKING_MODEL` | No | Gemini model; defaults to the configured application default |
| `OPENAI_RANKING_MODEL` | No | OpenAI model when that provider is selected |

Use App Runner's secret-reference support for provider credentials rather than
committing them or baking them into the image. Auto.dev and Gemini credentials
are read only by the API; the frontend receives only the API base URL.

The search limiter is an in-memory fixed-window limit shared by `/search` and
`/search/natural`, keyed by the final address in App Runner's
`X-Forwarded-For` header (or the direct client address when that header is
absent). It reduces casual abuse for a small public demo, but counters are
per-process and reset on restart/scale-out. Use a shared limiter or an upstream
edge control before relying on it for higher traffic or a strict spend ceiling.

The API returns sanitized messages for provider failures and does not return
provider exception text or credentials. Production FastAPI debug mode is
disabled even if `DEBUG=true` is accidentally set.

The default Nominatim resolver's cache and one-request-per-second throttle are
per process. That is suitable only for modest, user-driven demo traffic; App
Runner scale-out can increase aggregate geocoder traffic. Configure
`LOCATION_GEOCODER_BASE_URL` to a managed or self-hosted service before
sustained traffic.

## Frontend: S3 and CloudFront

Next.js is configured for static export. `next/image` runs unoptimized so
provider-supplied image URLs can be rendered without a Next image server.
Production builds use `/autoscout` as the base path and trailing-slash output;
development remains at `/`.

Build from `apps/web`, setting the public App Runner HTTPS URL at build time:

```bash
NEXT_PUBLIC_API_BASE_URL=https://<app-runner-service-url> npm run build
```

In PowerShell:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL = "https://<app-runner-service-url>"
npm.cmd run build
```

The static export is `apps/web/out/`. Upload the **contents** of that directory
to `s3://danielolowe-portfolio/autoscout/`, preserving the generated
`_next/` directory underneath that prefix. For example, after the build:

```bash
aws s3 sync apps/web/out/ s3://danielolowe-portfolio/autoscout/
```

The deployment command above is documentation only and has not been run.
`NEXT_PUBLIC_API_BASE_URL` is embedded in the public frontend at build time, so
it must be set to the eventual HTTPS App Runner URL before building the upload
artifact. If unset, production does not fall back to a localhost URL.
Development without this variable continues to use
`http://127.0.0.1:8000`.

## CloudFront path behavior

The base path prefixes generated scripts, styles, images, and Next links with
`/autoscout`. The exported root document is `index.html`, so a CloudFront
viewer-request rewrite is needed if the existing S3 origin does not already
serve directory index files: rewrite `/autoscout/` to
`/autoscout/index.html`. Redirect `/autoscout` to `/autoscout/` for consistent
trailing-slash behavior. Do not rewrite `_next/*` requests; the exported page
references them under `/autoscout/_next/`.

No custom error mapping or single-page-app fallback is needed for this
single-route export. An invalidation of `/autoscout/*` may be used after future
uploads to clear cached files; it is not needed to make the path resolve. No
CloudFront, DNS, or S3 resource changes have been made.

## CORS and local configuration

CORS compares origins, not URL paths. The `/autoscout/` deployment still has
the origin `https://danielolowe.com`; do not add `/autoscout` to
`CORS_ORIGINS`. The default allowed origins include
`http://localhost:3000`, `http://127.0.0.1:3000`, and
`https://danielolowe.com`. Configure a different production hostname as an
exact origin through `CORS_ORIGINS`; wildcard origins are rejected.

See [`apps/api/.env.example`](../apps/api/.env.example) and
[`apps/web/.env.example`](../apps/web/.env.example) for local variable names.
