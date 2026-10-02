FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
# Curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN uv sync --locked

EXPOSE 3000

HEALTHCHECK --start-period=1s \
    CMD curl --silent http://localhost:3000/health || exit 1

# Run the venv python directly instead of `uv run` — the venv is already
# installed by `uv sync` above, so the `uv` launcher (~56MB resident) is
# just sitting in memory doing nothing. Calling the venv python directly
# drops the container's idle memory by that whole overhead.
CMD ["/app/.venv/bin/python", "-m", "fastapi", "run", "api.py", "--port", "3000"]
