# Tried markitdown but it gives huge headers and footers from sites :(
# Maybe I'll use it for dealing with screenshots
"""
Some notes:
  - Zoom links don't work well with this
  - Youtube links barely work
"""

import json
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import httpx
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


def clean_url_for_domains(url: str) -> str:
    """Strip query parameters and fragments from URLs for specific domains."""
    parsed = urlparse(url)
    domains_to_strip = {"linkedin.com", "nextcity.org", "instagram.com"}
    # Check if the domain matches any in the strip list
    if any(domain in parsed.netloc for domain in domains_to_strip):
        # Remove query and fragment
        cleaned = urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, "", "")
        )
        return cleaned
    return url


def extract_youtube_video(url: str) -> ExtractedPage:
    tldw_url = "https://api.tldw.tube/api/summarize"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/json",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }
    response = httpx.post(tldw_url, json={"url": url}, headers=headers)
    response.raise_for_status()
    response_data = response.json()
    return ExtractedPage(
        text=response_data["summary"]["paragraph"],
        title=response_data["title"],
        url=url,
    )


def extract_page(url: str, notion_id: str) -> ExtractedPage:
    url = clean_url_for_domains(url)

    YOUTUBE_DOMAINS = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }
    if any(domain in url.lower() for domain in YOUTUBE_DOMAINS):
        return extract_youtube_video(url)

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
        "https://transalt.org/newsletter/turning-tragedy-into-action-how-we-can-end-traffic-violence-in-new-york",
        "dummy_id",
    )
    print(page)
