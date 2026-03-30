from contextlib import asynccontextmanager

import httpx
from fastapi import BackgroundTasks, FastAPI

from main import fill_empty_notion_rows


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - create async client
    import scrape_page

    scrape_page.async_client = httpx.AsyncClient(timeout=30.0)
    yield
    # Shutdown - clean up resources
    await scrape_page.async_client.aclose()


app = FastAPI(lifespan=lifespan)

# uv run fastapi dev api.py


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
async def read_root(background_tasks: BackgroundTasks):
    errors = await fill_empty_notion_rows(background_tasks)
    return {"errors": errors}
