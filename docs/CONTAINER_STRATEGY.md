# Container Strategy — NHL Scraper

## Overview

Containerize the NHL scraper for consistent deployment across:
- Local development
- GitHub Actions (scheduled scrapes)
- Self-hosted runners / home server
- Potential cloud deployment (AWS ECS, fly.io, etc.)

## Design Decisions

### Base Image
**Choice: `python:3.11-slim-bookworm`**
- Debian-based (broad compatibility)
- Slim variant (~45MB base vs ~350MB full)
- Python 3.11 matches project requirement
- `bookworm` is current stable Debian

### Build Strategy
**Multi-stage build:**
1. **Builder stage** — install build deps, compile wheels
2. **Runtime stage** — copy only what's needed

Benefits:
- Smaller final image (~150-200MB vs ~500MB+)
- No build tools in production
- Faster pulls, reduced attack surface

### Image Variants

| Tag | Purpose | Size Est. |
|-----|---------|-----------|
| `latest` / `0.1.0` | Production runtime | ~150MB |
| `dev` | With dev deps (pytest, ruff, mypy) | ~200MB |

### Data Persistence

```
Container paths:
/app/data/     → Scraped data (SQLite DB, exports)
/app/cache/    → HTTP response cache
/app/logs/     → Application logs (optional)
```

Mount strategy:
- **Local dev**: bind mounts to host directories
- **Production**: named volumes or cloud storage

### Environment Variables

```bash
# Database
NHL_SCRAPER_DB=sqlite:///data/nhl.db  # or postgresql://...

# Scraper behavior
NHL_SCRAPER_CACHE_DIR=/app/cache
NHL_SCRAPER_LOG_LEVEL=INFO
NHL_SCRAPER_RATE_LIMIT_MULTIPLIER=1.0  # slow down if needed

# Optional API keys (future)
HOCKEY_REF_API_KEY=
MONEYPUCK_API_KEY=
```

### Health & Observability

- No long-running HTTP server → no health endpoint needed
- Rely on exit codes for job success/failure
- Structured logs (JSON) for easy parsing

## Compose Architecture

```yaml
services:
  scraper:       # One-off scrape jobs
  scraper-cron:  # Scheduled scrapes (optional)
  db:            # PostgreSQL (optional, for production)
```

For simple use: just `scraper` service with SQLite.
For production: add `db` service, switch connection string.

## CI Integration

**Option A: Build in workflow, use for scrape**
```yaml
- name: Build container
  run: docker build -t nhl-stats .
- name: Run scrape
  run: docker run -v ./data:/app/data nhl-stats scrape --all
```

**Option B: Pull from registry**
```yaml
- name: Run scrape
  run: docker run -v ./data:/app/data ghcr.io/david/nhl-stats:latest scrape --all
```

Recommend Option B for scheduled scrapes (faster), Option A for CI (test current code).

## Security Considerations

1. Run as non-root user inside container
2. Read-only root filesystem (mount data as writable)
3. No unnecessary capabilities
4. Pin base image digests in production

## File Structure

```
nhl-stats/
├── Dockerfile           # Multi-stage production build
├── Dockerfile.dev       # Dev image with tools (optional)
├── docker-compose.yml   # Local development
├── docker-compose.prod.yml  # Production overrides (optional)
├── .dockerignore        # Exclude .venv, .git, etc.
└── .github/workflows/
    ├── ci.yml           # Add Docker build step
    ├── docker-publish.yml  # Build & push to GHCR
    └── scheduled-scrape.yml  # Use container
```

## Implementation Plan

1. Create `.dockerignore`
2. Create `Dockerfile` (multi-stage)
3. Create `docker-compose.yml`
4. Update CI workflow to build/test Docker image
5. Add `docker-publish.yml` for GHCR pushes
6. Update `scheduled-scrape.yml` to use container

## Quick Start (after implementation)

```bash
# Build locally
docker compose build

# Run interactive scrape
docker compose run --rm scraper scrape --source nhl-api

# Run full daily scrape
docker compose run --rm scraper scrape --all

# Development shell
docker compose run --rm scraper bash
```
