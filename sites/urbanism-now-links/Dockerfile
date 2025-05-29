FROM ghcr.io/astral-sh/uv:python3.13-alpine
# Curl for scheduled runs
RUN apk --no-cache add curl

WORKDIR /app

COPY . /app

RUN uv sync --locked

EXPOSE 3000

CMD ["uv", "run", "fastapi", "run", "api.py", "--port", "3000"]
