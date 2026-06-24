"""
Gets all the pages from Notion without AI summaries or regions and updates them with the results of the LLM.
"""

import time
from pprint import pprint

from notion import (
    LLM_FIELDS,
    NotionRowInput,
    NotionRowURL,
    get_notion_rows_without_ai_summary,
    slugify,
    update_notion_row,
)
from openrouter import get_llm_categorizations
from scrape_page import extract_page

# Track notion IDs that failed extraction to avoid infinite retries
_failed_notion_ids: set[str] = set()


async def fill_empty_notion_rows(background_tasks=None):
    errors = []
    for row in get_notion_rows_without_ai_summary():
        if row.id in _failed_notion_ids:
            continue
        try:
            await fill_notion_row(row, background_tasks)
        except Exception as e:
            print(f"Error: {e}")
            _failed_notion_ids.add(row.id)
            errors.append(str(e))
    return errors


async def fill_notion_row(row: NotionRowURL, background_tasks=None) -> None:
    print(row)
    page = await extract_page(row.url, row.id, background_tasks)
    print(page)

    llm_results = get_llm_categorizations(page)
    print(llm_results)

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
        # Auto-wire all LLM-extracted fields (defined in notion.LLM_FIELDS)
        **{f: getattr(llm_results, f) for f in LLM_FIELDS},
    )
    pprint(row_input)

    update_notion_row(row_input)


if __name__ == "__main__":
    import asyncio

    import httpx

    # Initialize async client for standalone execution
    import scrape_page

    scrape_page.async_client = httpx.AsyncClient(timeout=30.0)

    async def run_loop():
        try:
            while True:
                try:
                    await fill_empty_notion_rows()
                except Exception as e:
                    print(f"Error: {e}")
                print("checking again in 60 seconds...")
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass
        finally:
            client = scrape_page.async_client
            if client:
                await client.aclose()

    asyncio.run(run_loop())
