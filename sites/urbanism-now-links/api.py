"""Lean API server.

Only imports the cheap Notion query + batch dispatcher — the heavy work (scrape,
LLM, markitdown) runs in a short-lived `python -m worker` subprocess via
batch.py, so this process stays ~40MB instead of ~250MB.

`GET /` queries Notion for rows missing an AI summary and dispatches each batch
of up to batch.MAX_BATCH rows to a worker subprocess. Failed rows are remembered
in-process so the next minute's check doesn't retry them.
"""

import sys
from typing import Set

from fastapi import FastAPI

from batch import run_all_batches
from notion import get_notion_rows_without_ai_summary

app = FastAPI()

# Track notion IDs that failed processing so we don't retry them every minute.
# Lives in-process (a set of strings, ~0 KB); resets when the server restarts.
_failed_notion_ids: Set[str] = set()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def read_root():
    try:
        rows = [
            r
            for r in get_notion_rows_without_ai_summary()
            if r.id not in _failed_notion_ids
        ]
    except Exception as e:
        return {"error": str(e), "results": []}

    if not rows:
        return {"results": [], "failed": sorted(_failed_notion_ids)}

    results = []
    for _, batch_results in run_all_batches(rows):
        for res in batch_results:
            if not res.get("ok"):
                _failed_notion_ids.add(res["id"])
        results.extend(batch_results)

    return {
        "results": results,
        "failed": sorted(_failed_notion_ids),
    }
