# syntax=docker/dockerfile:1

# =============================================================================
# NHL Scraper - Multi-stage Dockerfile
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

# Prevent Python from writing bytecode and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first (better layer caching)
COPY pyproject.toml README.md ./

# Create wheels for all dependencies
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -e .

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# Labels
LABEL org.opencontainers.image.title="NHL Stats" \
      org.opencontainers.image.description="NHL analytics and statistics" \
      org.opencontainers.image.source="https://github.com/david/nhl-stats" \
      org.opencontainers.image.licenses="MIT"

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # App defaults
    NHL_STATS_DB=sqlite:///data/nhl.db \
    NHL_STATS_CACHE_DIR=/app/cache \
    NHL_STATS_LOG_LEVEL=INFO

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/* \
    # Create non-root user
    && groupadd --gid 1000 scraper \
    && useradd --uid 1000 --gid scraper --shell /bin/bash --create-home scraper

WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/* \
    && rm -rf /tmp/wheels

# Copy application code
COPY --chown=scraper:scraper src/ ./src/
COPY --chown=scraper:scraper pyproject.toml README.md ./

# Install the package itself
RUN pip install --no-cache-dir -e . \
    && mkdir -p /app/data /app/cache \
    && chown -R scraper:scraper /app

# Switch to non-root user
USER scraper

# Default volumes
VOLUME ["/app/data", "/app/cache"]

# Default command - show help
ENTRYPOINT ["nhl-stats"]
CMD ["--help"]
