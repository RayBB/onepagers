# Tried markitdown but it gives huge headers and footers from sites :(
# Maybe I'll use it for dealing with screenshots
"""
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert_url("https://nextcity.org/urbanist-news/in-nashville-cdfis-are-helping-convert-motels-into-affordable-housing")
print(result.text_content)
"""

import json
from dataclasses import dataclass

import trafilatura


@dataclass
class ExtractedPage:
    text: str
    title: str
    author: str
    date: str


def extract_page(url: str) -> ExtractedPage:
    downloaded = trafilatura.fetch_url(url)
    result = trafilatura.extract(downloaded, with_metadata=True, output_format="json")
    result = json.loads(result)

    return ExtractedPage(
        text=result["text"],
        title=result["title"],
        author=result["author"],
        date=result["date"],  # seems to be YYYY-MM-DD
    )


if __name__ == "__main__":
    page = extract_page(
        "https://transalt.org/newsletter/turning-tragedy-into-action-how-we-can-end-traffic-violence-in-new-york"
    )
    print(page)
