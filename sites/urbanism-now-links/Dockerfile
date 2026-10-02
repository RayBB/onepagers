# Stage 1: build the Go checker (the lean always-on server, ~11MB RSS).
FROM golang:1.26-bookworm AS checker-builder
WORKDIR /src
COPY checker/go.mod checker/main.go ./
RUN CGO_ENABLED=0 go build -o /checker .

# Stage 2: runtime — Python venv (for the worker) + the Go checker binary.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
# Curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN uv sync --locked

COPY --from=checker-builder /checker /app/checker-bin

EXPOSE 3000

HEALTHCHECK --start-period=1s \
    CMD curl --silent http://localhost:3000/health || exit 1

# The Go checker is the always-on server (~11MB RSS). It spawns `python -m
# worker` as a short-lived subprocess for each batch of rows; the heavy stack
# (litellm, instructor, trafilatura, markitdown) lives only in that subprocess.
CMD ["/app/checker-bin"]
