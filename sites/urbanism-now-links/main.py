"""
Gets all the pages from Notion without AI summaries or regions and updates them with the results of the LLM.
"""

import time
from pprint import pprint

from notion import (
    NotionRowInput,
    NotionRowURL,
    get_notion_rows_without_ai_summary,
    update_notion_row,
)
from openrouter import get_llm_categorizations
from scrape_page import extract_page


async def fill_empty_notion_rows(background_tasks=None):
    errors = []
    for row in get_notion_rows_without_ai_summary():
        try:
            await fill_notion_row(row, background_tasks)
        except Exception as e:
            print(f"Error: {e}")
            errors.append(str(e))
    return errors


async def fill_notion_row(row: NotionRowURL, background_tasks=None) -> None:
    print(row)
    page = await extract_page(row.url, row.id, background_tasks)
    print(page)

    llm_results = get_llm_categorizations(page)
    print(llm_results)

    row_input = NotionRowInput(
        url=page.url,
        notion_row_id=row.id,
        title=page.title or llm_results.title,
        summary=llm_results.summary,
        region=llm_results.region,
        topics=llm_results.topics,
        other_tags=llm_results.other_tags,
        vibe=llm_results.vibe,
        date=page.date or llm_results.date,
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
        while True:
            try:
                await fill_empty_notion_rows()
            except Exception as e:
                print(f"Error: {e}")
            print("checking again in 60 seconds...")
            await asyncio.sleep(60)

    try:
        asyncio.run(run_loop())
    finally:
        asyncio.run(scrape_page.async_client.aclose())
