import os
from dataclasses import dataclass
from pprint import pprint
from typing import Any, Dict, List

from cachetools import TTLCache, cached
from dotenv import load_dotenv
from notion2md.exporter.block import StringExporter
from notion_client import Client

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])

DATABASE_ID = os.environ["NOTION_DATABASE_ID"]


@cached(TTLCache(maxsize=1, ttl=300))
def get_db_properties() -> Dict[str, Any]:
    """
        https://developers.notion.com/reference/retrieve-a-database
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
    db_schema = notion.databases.retrieve(DATABASE_ID)
    return db_schema["properties"]


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


@dataclass
class NotionRowInput:
    url: str = None
    topics: List[str] = None
    other_tags: List[str] = None
    notion_row_id: str = None  # Only for updating row
    title: str = None
    summary: str = None
    region: str = None
    vibe: str = None
    date: str = None  # YYYY-MM-DD


def create_notion_input_properties(row_input: NotionRowInput) -> Dict[str, Any]:
    properties = {}
    if row_input.title:
        properties["Title"] = [{"text": {"content": row_input.title}}]
    if row_input.url:
        properties["URL"] = row_input.url
    if row_input.summary:
        properties["A.I. Summary"] = [{"text": {"content": row_input.summary}}]
    if row_input.region:
        properties["Region"] = {"name": row_input.region}
    if row_input.vibe:
        properties["Vibe"] = {
            "name": row_input.vibe
        }  # Not a multiselect, can only have one
    if row_input.topics:
        properties["Topic"] = [{"name": topic} for topic in row_input.topics]
    if row_input.other_tags:
        properties["Other Tags"] = [{"name": tag} for tag in row_input.other_tags]
    if row_input.date:
        properties["Publication Date"] = {"start": row_input.date}  # YYYY-MM-DD
    return properties


# Todo I think we'll be updating Notion rows rather than creating them.
def create_notion_row(properties):
    # https://developers.notion.com/reference/post-page
    PARENT = {"type": "database_id", "database_id": DATABASE_ID}
    o = notion.pages.create(parent=PARENT, properties=properties)
    pprint(o)
    return o


@dataclass
class NotionRowURL:
    id: str
    url: str


def get_notion_rows_without_ai_summary() -> List[NotionRowURL]:
    # No AI summary and no region so we don't get old articles
    filter = {
        "and": [
            {"property": "A.I. Summary", "rich_text": {"is_empty": True}},
            # {"property": "Region", "select": {"is_empty": True}},
        ]
    }
    results = notion.databases.query(**{"database_id": DATABASE_ID, "filter": filter})
    notion_rows = []
    for result in results["results"]:
        notion_row = NotionRowURL(
            id=result["id"], url=result["properties"]["URL"]["url"]
        )
        notion_rows.append(notion_row)
    return notion_rows


def update_notion_row(row: NotionRowInput) -> None:
    notion.pages.update(
        page_id=row.notion_row_id,
        properties=create_notion_input_properties(row),
    )


def get_notion_page_contents_as_md(page_id: str) -> str:
    return StringExporter(block_id=page_id).export()


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
