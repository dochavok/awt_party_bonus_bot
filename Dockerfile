# The bot's image (requirements section 12, DP-1 to DP-4). See docs/deployment.md.
#
# Built by Fly.io on every deploy, or locally with:
#   docker build -t awt-bonus .
# The database lives on a volume mounted at /data (DB-2); secrets come from the
# environment (NF-9). Nothing secret is in the image.
# Base images are pinned by digest; Dependabot keeps them current (NF-12).

FROM ghcr.io/astral-sh/uv:0.12.19@sha256:04d046b13e60d6bcec73cbc5e1cad25d680dea90c8573340950a0ac2d1aef424 AS uv

# ---------------------------------------------------------------- build: the virtual environment
FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Dependencies first, so a code-only change reuses this layer. The lock file has
# hashes (section 12); --locked refuses anything that doesn't match it.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ---------------------------------------------------------------- run
FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
RUN useradd --system --uid 1000 --user-group --no-create-home --home-dir /app bot
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY catalog ./catalog
COPY config ./config
COPY alembic.ini ./
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
COPY docker/awt-admin /usr/local/bin/awt-admin
RUN chmod 0755 /usr/local/bin/entrypoint /usr/local/bin/awt-admin

ARG GIT_SHA=dev
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite+aiosqlite:////data/awt-bonus.db \
    GIT_SHA=$GIT_SHA

# /data is deliberately not created here: without a volume there, the bot refuses
# to start (DB-2) instead of writing to storage that disappears.
ENTRYPOINT ["entrypoint"]
CMD ["python", "-m", "awt_bonus"]
