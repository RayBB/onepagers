FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY . /app

RUN uv sync --locked

EXPOSE 3000

CMD ["uv", "run", "fastapi", "run", "api.py", "--port", "3000"]
