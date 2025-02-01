import json
import os
from dataclasses import dataclass
from typing import Any, List

from dotenv import load_dotenv
from openai import OpenAI

from notion import get_select_options
from scrape_page import ExtractedPage

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPEN_ROUTER_TOKEN"],
)


def build_schema_properties(page: ExtractedPage) -> dict[str, Any]:
    properties = {
        "Topic": {
            "type": "array",
            "items": {
                "enum": get_select_options("Topic"),
                "description": "The topics that best map to this content.",
                "type": "string",
            },
        },
        "Vibe": {
            "description": "Is this content about something positive people want to see more of in the world or negative that people want less of in the world?",
            "enum": get_select_options("Vibe"),
            "type": "string",
        },
        "Region": {
            "description": "The region that this content is about. If it doesn't specify, where does it originate from?",
            "enum": get_select_options("Region"),
            "type": "string",
        },
        "Other Tags": {
            "type": "array",
            "items": {
                "enum": get_select_options("Other Tags"),
                "description": "The topics that best represent this content.",
                "type": "string",
            },
        },
        "Summary": {
            "type": "string",
            "description": "A 1-2 sentence summary of the content. The target audience is people who are interested in urbanism. Don't be afraid of jargon but focus on clarity.",
        },
    }
    if not page.title:
        properties["Title"] = {
            "type": "string",
            "description": "The title of the content. If none exists, create one.",
        }
    if not page.author:
        properties["Author"] = {
            "type": "string",
            "description": "The author of the content.",
        }
    if not page.date:
        properties["Date"] = {
            "type": "string",
            "description": "The date the content was written in YYYY-MM-DD format.",
        }
    return properties


@dataclass
class LLM_Results:
    vibe: str = None
    other_tags: List[str] = None
    region: str = None
    topics: List[str] = None
    summary: str = None
    title: str = None
    author: str = None
    date: str = None


def get_llm_categorizations(
    page: ExtractedPage,
) -> LLM_Results:
    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "https://urbanismnow.com",  # Optional. Site URL for rankings on openrouter.ai.
            "X-Title": "Urbanism Now",  # Optional. Site title for rankings on openrouter.ai.
        },
        model="google/gemini-flash-1.5",
        messages=[
            {
                "role": "user",
                "content": f"Url: {page.url}\nTitle: {page.title}\nText: {page.text}\nFill out the json schema about the above content",
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "content_check",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": build_schema_properties(page),
                    "required": ["Topic", "Vibe", "Region", "Summary"],
                    "additionalProperties": True,
                },
            },
        },
    )
    output_json = json.loads(completion.choices[0].message.content)
    return LLM_Results(
        vibe=output_json.get("Vibe"),
        other_tags=output_json.get("Other Tags", []),
        region=output_json.get("Region"),
        topics=output_json.get("Topic", []),
        summary=output_json.get("Summary"),
        title=output_json.get("Title"),
        author=output_json.get("Author"),
        date=output_json.get("Date"),
    )


if __name__ == "__main__":
    output = get_llm_categorizations(
        "Caltrain’s Electric Fleet More Efficient than Expected", ""
    )
    print(output)
