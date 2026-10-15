# ==============================================================================
# Multi-Stage Dockerfile for TriagePilot (Google Cloud Run Ready)
# Stage 1: Build React 18 / Tailwind Cockpit UI
# Stage 2: Python 3.11 Slim Backend & Unified Static Serving
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: UI Builder
# ------------------------------------------------------------------------------
FROM node:20-alpine AS ui-builder

WORKDIR /build/ui

# Install dependencies with caching
COPY ui/package.json ui/package-lock.json ./
RUN npm ci

# Copy UI source code and build production assets
COPY ui/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Runtime Production Image
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS production

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Install system dependencies (git required for GitPort / clientrepo inspection, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code, profiles, fixtures, and scenario data
COPY engine/ /app/engine/
COPY api/ /app/api/
COPY eval/ /app/eval/
COPY profiles/ /app/profiles/
COPY data/ /app/data/
COPY scripts/ /app/scripts/

# Restore clientrepo .git history from bundle (since .dockerignore/.gcloudignore strip nested .git dirs)
RUN if [ ! -d /app/data/clientrepo/.git ] && [ -f /app/data/clientrepo.bundle ]; then \
        git clone /app/data/clientrepo.bundle /tmp/clientrepo && \
        mv /tmp/clientrepo/.git /app/data/clientrepo/.git && \
        rm -rf /tmp/clientrepo && \
        git -C /app/data/clientrepo reset --hard HEAD; \
    fi && git config --system --add safe.directory /app/data/clientrepo

# Copy built React Cockpit from Stage 1 into /app/ui/dist
COPY --from=ui-builder /build/ui/dist /app/ui/dist

# Expose Cloud Run HTTP port
EXPOSE 8080

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/readyz || exit 1

# Start FastAPI application via Uvicorn
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
