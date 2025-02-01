import os
from dataclasses import dataclass
from pprint import pprint
from typing import Any, Dict, List

from cachetools import TTLCache, cached
from dotenv import load_dotenv
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
    url: str
    topics: List[str]
    other_tags: List[str]
    title: str = None
    summary: str = None
    region: str = None
    vibe: str = None
    date: str = None  #: datetime.date


def create_notion_input_properties(row_input: NotionRowInput) -> Dict[str, Any]:
    # date_string = row_input.date.strftime("%Y-%m-%d")
    date_string = row_input.date
    return {
        "Title": [{"text": {"content": row_input.title}}],
        "URL": row_input.url,
        "A.I. Summary": [{"text": {"content": row_input.summary}}],
        "Region": {"name": row_input.region},
        "Vibe": {"name": row_input.vibe},  # Not a multiselect, can only have one
        "Topic": [{"name": topic} for topic in row_input.topics],
        "Other Tags": [{"name": tag} for tag in row_input.other_tags],
        "Publication Date": {"start": date_string},  # YYYY-MM-DD
    }


# Todo I think we'll be updating Notion rows rather than creating them.
def create_notion_row(properties):
    # https://developers.notion.com/reference/post-page
    PARENT = {"type": "database_id", "database_id": DATABASE_ID}
    o = notion.pages.create(parent=PARENT, properties=properties)
    pprint(o)
    return o


if __name__ == "__main__":
    properties = get_db_properties()
    pprint(properties)

    pprint(get_select_options("Vibe"))
    pprint(get_select_options("Region"))
    pprint(get_select_options("Topic"))
    pprint(get_select_options("Other Tags"))
