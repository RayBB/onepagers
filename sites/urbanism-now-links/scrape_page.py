# Tried markitdown but it gives huge headers and footers from sites :(
# Maybe I'll use it for dealing with screenshots
"""
Some notes:
  - Zoom links don't work well with this
  - Youtube links barely work
"""

import json
from dataclasses import dataclass

import trafilatura
from markitdown import MarkItDown

from notion import get_notion_page_contents_as_md


@dataclass
class ExtractedPage:
    text: str
    url: str
    title: str = None
    author: str = None
    date: str = None


def extract_page(url: str, notion_id: str) -> ExtractedPage:
    try:
        downloaded = trafilatura.fetch_url(url)
        extracted = trafilatura.extract(
            downloaded, with_metadata=True, output_format="json"
        )
        if extracted:
            result = json.loads(extracted)
            return ExtractedPage(
                text=result["text"],
                title=result["title"],
                author=result["author"],
                date=result["date"],  # seems to be YYYY-MM-DD
                url=url,
            )
    except Exception as e:
        print(e)

    try:
        md = MarkItDown()
        md_result = md.convert_url(url)
        return ExtractedPage(
            text=md_result.text_content, title=md_result.title, url=url
        )

    except Exception as e:
        print(e)
        md_result = get_notion_page_contents_as_md(page_id=notion_id)
        if md_result:
            return ExtractedPage(text=md_result, url=url)

        IA_PREFIX = "https://web.archive.org/web/"
        if IA_PREFIX not in url:
            return extract_page(f"{IA_PREFIX}{url}", notion_id)
        raise Exception(f"Could not get Notion page contents for {url}")


if __name__ == "__main__":
    page = extract_page(
        "https://transalt.org/newsletter/turning-tragedy-into-action-how-we-can-end-traffic-violence-in-new-york"
    )
    print(page)
