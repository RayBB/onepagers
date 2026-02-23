from fastapi import FastAPI

from main import fill_empty_notion_rows

app = FastAPI()

# uv run fastapi dev api.py


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def read_root():
    errors = fill_empty_notion_rows()
    return {"errors": errors}
