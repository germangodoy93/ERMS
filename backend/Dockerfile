# syntax=docker/dockerfile:1
# ERMS backend image. Same image for local docker compose and Railway.

FROM ghcr.io/astral-sh/uv:0.13.9 AS uv

FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv

# --- Dependencies layer (cached unless pyproject/uv.lock change) -------------
FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

# --- Development: includes test/lint tooling, code mounted as a volume -------
FROM deps AS dev
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project
COPY . .
CMD ["sh", "scripts/start.sh", "--reload"]

# --- Production --------------------------------------------------------------
FROM base AS prod
COPY --from=deps /opt/venv /opt/venv
COPY . .
RUN useradd --system --uid 10001 --no-create-home erms && chown -R erms /app
USER erms
EXPOSE 8000
CMD ["sh", "scripts/start.sh"]
