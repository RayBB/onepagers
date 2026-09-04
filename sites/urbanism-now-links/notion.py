import os
import re
from dataclasses import dataclass
from pprint import pprint
from typing import Any, Dict, List, Optional

from cachetools import TTLCache, cached
from dotenv import load_dotenv
from notion_client import Client

from notion_to_md import get_page_body_as_md

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])

DATABASE_ID = os.environ["NOTION_DATABASE_ID"]


@cached(TTLCache(maxsize=1, ttl=300))
def get_data_source_id() -> str:
    """Get the data source ID from the database.

    Best practice: Extract data_source_id efficiently with minimal API calls.
    This avoids retrieving properties when we only need the data source ID.

    https://developers.notion.com/reference/retrieve-database
    """
    db_schema = notion.databases.retrieve(DATABASE_ID)
    return db_schema["data_sources"][0]["id"]  # ty: ignore


@cached(TTLCache(maxsize=1, ttl=300))
def get_db_properties() -> Dict[str, Any]:
    """Get database properties from the first data source.

    https://developers.notion.com/reference/retrieve-a-database

    In notion-client 3.0.0, properties are in data_source, not directly in database.
    Properties look something like this:
      {
            "URL": { "id": "c%40%40%3C", "name": "URL", "type": "url", "url": {} },
            "Used in Newsletter Number": { "id": "OO%3B%7D", "name": "Used in Newsletter Number", "rich_text": {}, "type": "rich_text" },
            "Vibe": {"id": "n%5Eb%3B", "name": "Vibe",
                    "select": { "options": [
                                    { "color": "red", "description": None, "id": "]Qo}", "name": "Negative" },
                                    { "color": "green", "description": None, "id": "P>RR", "name": "Positive" }
                    ]},
                    "type": "select"
            }
    }
    /// We cannot use these fields when updating: rollup, created_by, created_time, last_edited_by, or last_edited_time
    """
    data_source_id = get_data_source_id()
    data_source = notion.data_sources.retrieve(data_source_id)
    return data_source["properties"]  # ty: ignore


def get_select_options(field_name, db_properties=None):
    """
    Retrieves the names of options for a select or multi_select type field from the database properties.

    :param field_name: The name of the field to check.
    :param db_properties: The dictionary containing database properties.
    :return: A list of option names if the field type is 'select' or 'multi_select', otherwise an empty list.
    """
    if db_properties is None:
        db_properties = get_db_properties()
    if field_name in db_properties:
        field = db_properties[field_name]
        if field.get("type") in ("select", "multi_select"):
            return [option["name"] for option in field[field["type"]]["options"]]
    return []


# Maps Python field name -> (Notion column name, Notion type)
# To add a new field:
#   1. Add a field to NotionRowInput and NotionRowInput dataclass below
#   2. Add a line to FIELD_MAP
#   3. If the LLM should extract it, add the field name to LLM_FIELDS
#   4. Add a Field to LLM_Results in openrouter.py
# No other changes needed — create_notion_input_properties and main.py auto-wire from FIELD_MAP.
FIELD_MAP: Dict[str, tuple[str, str]] = {
    "url": ("URL", "url"),
    "title": ("Title", "title"),
    "summary": ("A.I. Summary", "rich_text"),
    "short_social_post": ("Short Social Media Post", "rich_text"),
    "hashtags": ("Hashtags", "rich_text"),
    "region": ("Region", "select"),
    "vibe": ("Vibe", "select"),
    "topics": ("Topic", "multi_select"),
    "other_tags": ("Other Tags", "multi_select"),
    "date": ("Publication Date", "date"),
    "job_title": ("job_title", "rich_text"),
    "job_description": ("job_description", "rich_text"),
    "job_organization": ("job_organization", "rich_text"),
    "job_location": ("job_location", "rich_text"),
    "job_location_type": ("job_location_type", "select"),
    "job_salary": ("job_salary", "rich_text"),
    "job_deadline": ("job_deadline", "rich_text"),
    "job_slug": ("job_slug", "rich_text"),
}

# Set of field names that the LLM extracts (auto-wired in main.py)
LLM_FIELDS = {
    "summary",
    "short_social_post",
    "hashtags",
    "region",
    "vibe",
    "topics",
    "other_tags",
    "job_title",
    "job_description",
    "job_organization",
    "job_location",
    "job_location_type",
    "job_salary",
    "job_deadline",
}


@dataclass
class NotionRowInput:
    url: Optional[str] = None
    topics: Optional[List[str]] = None
    other_tags: Optional[List[str]] = None
    notion_row_id: Optional[str] = None  # Only for updating row
    title: Optional[str] = None
    summary: Optional[str] = None
    short_social_post: Optional[str] = None
    hashtags: Optional[str] = None
    region: Optional[str] = None
    vibe: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    job_organization: Optional[str] = None
    job_location: Optional[str] = None
    job_location_type: Optional[str] = None
    job_salary: Optional[str] = None
    job_deadline: Optional[str] = None
    job_slug: Optional[str] = None


def slugify(text: str) -> str:
    """Convert text to kebab-case slug (lowercase, hyphens, no special chars)."""
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text).strip("-")


def _normalize_date(value: str) -> str:
    """Normalize a date string to ISO 8601 (YYYY-MM-DD) for Notion's date type."""
    try:
        from dateutil import parser

        return parser.parse(value).strftime("%Y-%m-%d")
    except Exception:
        return value


def _format_notion_value(value: Any, notion_type: str) -> Any:
    """Format a Python value into the JSON structure Notion expects for a given column type."""
    if notion_type in ("title", "rich_text"):
        return [{"text": {"content": value}}]
    elif notion_type == "url":
        return value  # plain URL string
    elif notion_type == "select":
        return {"name": value}
    elif notion_type == "multi_select":
        return [{"name": v} for v in value]
    elif notion_type == "date":
        return {"start": _normalize_date(value)}
    raise ValueError(f"Unknown Notion type: {notion_type}")


def create_notion_input_properties(row_input: NotionRowInput) -> Dict[str, Any]:
    """Build the Notion API properties dict from a NotionRowInput.
    Auto-wires all fields defined in FIELD_MAP — add new fields there instead of adding if-blocks here."""
    properties = {}
    for field_name, (notion_col, notion_type) in FIELD_MAP.items():
        value = getattr(row_input, field_name, None)
        if not value:  # skip None, empty string, empty list, etc.
            continue
        properties[notion_col] = _format_notion_value(value, notion_type)
    return properties


# Todo I think we'll be updating Notion rows rather than creating them.
def create_notion_row(properties):
    """Create a new row in the data source."""
    data_source_id = get_data_source_id()
    PARENT = {"type": "data_source_id", "data_source_id": data_source_id}
    o = notion.pages.create(parent=PARENT, properties=properties)
    pprint(o)
    return o


@dataclass
class NotionRowURL:
    id: str
    url: str


def get_notion_rows_without_ai_summary() -> List[NotionRowURL]:
    """Query rows without AI summary from data source."""
    data_source_id = get_data_source_id()
    filter = {
        "and": [
            {"property": "A.I. Summary", "rich_text": {"is_empty": True}},
            # {"property": "Region", "select": {"is_empty": True}},
        ]
    }
    results = notion.data_sources.query(data_source_id=data_source_id, filter=filter)
    notion_rows = []
    for result in results["results"]:  # ty: ignore
        notion_row = NotionRowURL(
            id=result["id"], url=result["properties"]["URL"]["url"]
        )
        notion_rows.append(notion_row)
    return notion_rows


def update_notion_row(row: NotionRowInput) -> None:
    if row.notion_row_id is None:
        return
    notion.pages.update(
        page_id=row.notion_row_id,
        properties=create_notion_input_properties(row),
    )


def get_notion_page_contents_as_md(page_id: str) -> str:
    return get_page_body_as_md(page_id, notion)


def get_notion_page_title(page_id: str) -> str | None:
    try:
        page = notion.pages.retrieve(page_id)
        properties = page.get("properties", {})  # ty: ignore
        for prop_value in properties.values():
            if prop_value.get("type") == "title":
                texts = prop_value.get("title", [])
                if texts:
                    return "".join(t.get("plain_text", "") for t in texts)
    except Exception:
        pass
    return None


if __name__ == "__main__":
    # properties = get_db_properties()
    # pprint(properties)

    # pprint(get_select_options("Vibe"))
    # pprint(get_select_options("Region"))
    # pprint(get_select_options("Topic"))
    # pprint(get_select_options("Other Tags"))
    r = get_notion_rows_without_ai_summary()
    pprint(r)
    input = NotionRowInput(notion_row_id=r[0].id, title="Test3")
    update_notion_row(input)
