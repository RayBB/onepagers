from contextlib import asynccontextmanager

from fastapi import FastAPI

from main import fill_empty_notion_rows


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown - clean up resources
    from scrape_page import http_client

    http_client.close()


app = FastAPI(lifespan=lifespan)

# uv run fastapi dev api.py


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def read_root():
    errors = fill_empty_notion_rows()
    return {"errors": errors}
