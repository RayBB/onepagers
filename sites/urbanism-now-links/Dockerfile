FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
# Curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN uv sync --locked

EXPOSE 3000

HEALTHCHECK --start-period=1s \
    CMD curl --silent http://localhost:3000/health || exit 1

CMD ["uv", "run", "fastapi", "run", "api.py", "--port", "3000"]
