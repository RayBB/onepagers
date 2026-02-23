FROM ghcr.io/astral-sh/uv:python3.13-alpine
# Curl for health checks
RUN apk --no-cache add curl

WORKDIR /app

COPY . /app

RUN uv sync --locked

EXPOSE 3000

HEALTHCHECK --start-period=1s \
    CMD curl --silent http://localhost:3000/health || exit 1

CMD ["uv", "run", "fastapi", "run", "api.py", "--port", "3000"]
