"""Heavy per-row processing, isolated in a subprocess so its memory is reclaimed on exit.

Invoked by batch.py / api.py / main.py as:
    python -m worker
with a JSON array of {"id", "url"} objects on stdin. Writes a JSON array of
{"id", "ok", "error"?} results to stdout and exits.

All heavy imports (litellm, instructor, trafilatura, markitdown) live here so
the long-lived API server never has to load them.
"""

import asyncio
import json
import sys
from pprint import pprint

import httpx

import scrape_page
from notion import (
    LLM_FIELDS,
    NotionRowInput,
    NotionRowURL,
    slugify,
    update_notion_row,
)
from openrouter import get_llm_categorizations
from scrape_page import extract_page


async def fill_notion_row(row: NotionRowURL) -> dict:
    """Process one row. Returns a result dict for the caller."""
    print(row, file=sys.stderr)
    try:
        page = await extract_page(row.url, row.id)
        print(page, file=sys.stderr)

        llm_results = get_llm_categorizations(page)
        print(llm_results, file=sys.stderr)

        slug_parts = []
        if llm_results.job_title:
            slug_parts.append(slugify(llm_results.job_title))
        if llm_results.job_location:
            slug_parts.append(slugify(llm_results.job_location))
        slug_parts.append(row.id[-6:])
        job_slug = "-".join(slug_parts)

        row_input = NotionRowInput(
            url=page.url,
            notion_row_id=row.id,
            title=page.title or llm_results.title,
            date=page.date or llm_results.date,
            job_slug=job_slug,
            source=page.source,
            # Auto-wire all LLM-extracted fields (defined in notion.LLM_FIELDS)
            **{f: getattr(llm_results, f) for f in LLM_FIELDS},
        )
        pprint(row_input, stream=sys.stderr)

        update_notion_row(row_input)
        return {"id": row.id, "ok": True}
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return {"id": row.id, "ok": False, "error": str(e)}


async def run_rows(rows: list[NotionRowURL]) -> list[dict]:
    """Set up the shared async HTTP client, process each row, then tear down."""
    scrape_page.async_client = httpx.AsyncClient(timeout=30.0)
    try:
        return [await fill_notion_row(row) for row in rows]
    finally:
        await scrape_page.async_client.aclose()


def main() -> None:
    # Read [{"id": ..., "url": ...}, ...] from stdin.
    data = json.load(sys.stdin)
    rows = [NotionRowURL(id=r["id"], url=r["url"]) for r in data]

    # While the heavy pipeline runs, redirect stdout to stderr so any stray
    # print()/pprint() (ours or from deps) can't corrupt the JSON result we
    # write to the real stdout afterwards. The result is the only thing that
    # ever goes to the real stdout.
    real_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        results = asyncio.run(run_rows(rows))
    finally:
        sys.stdout = real_stdout
    json.dump(results, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
