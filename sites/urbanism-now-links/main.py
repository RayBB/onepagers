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


def fill_empty_notion_rows():
    for row in get_notion_rows_without_ai_summary():
        try:
            fill_notion_row(row)
        except Exception as e:
            print(f"Error: {e}")


def fill_notion_row(row: NotionRowURL) -> None:
    print(row)
    page = extract_page(row.url, row.id)
    print(page)

    llm_results = get_llm_categorizations(page)
    print(llm_results)

    row_input = NotionRowInput(
        url=row.url,
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
    while True:
        try:
            fill_empty_notion_rows()
        except Exception as e:
            print(f"Error: {e}")
        print("checking again in 60 seconds...")
        time.sleep(60)
