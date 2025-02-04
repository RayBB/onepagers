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


@dataclass
class ExtractedPage:
    text: str
    url: str
    title: str = None
    author: str = None
    date: str = None


def extract_page(url: str) -> ExtractedPage:
    try:
        downloaded = trafilatura.fetch_url(url)
        result = trafilatura.extract(
            downloaded, with_metadata=True, output_format="json"
        )
        result = json.loads(result)
    except Exception as e:
        print(e)
        md = MarkItDown()
        md_result = md.convert_url(url)
        result = {
            "text": md_result.text_content,
            "title": md_result.title,
            "author": None,
            "date": None,
        }

    return ExtractedPage(
        text=result["text"],
        title=result["title"],
        author=result["author"],
        date=result["date"],  # seems to be YYYY-MM-DD
        url=url,
    )


if __name__ == "__main__":
    page = extract_page(
        "https://transalt.org/newsletter/turning-tragedy-into-action-how-we-can-end-traffic-violence-in-new-york"
    )
    print(page)
