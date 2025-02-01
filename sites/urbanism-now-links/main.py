"""
We have a URL. We are going to make a call to fetch the text of that URL. Then we are going to send that text to OpenAPI or ChowJPT and then we're going to form a printing of the output.
"""

from notion import NotionRowInput, create_notion_input_properties, create_notion_row
from openrouter import get_llm_categorizations
from scrape_page import extract_page

URL = "https://www.theguardian.com/world/2025/jan/24/bangkok-pollution-hundreds-schools-closed-free-public-transport"

page = extract_page(URL)
print(page)

llm_results = get_llm_categorizations(page.title, page.text)
print(llm_results)

row_input = NotionRowInput(
    url=URL,
    title=page.title,
    summary=llm_results.summary,
    region=llm_results.region,
    topics=llm_results.topics,
    other_tags=llm_results.other_tags,
    vibe=llm_results.vibe,
    date=page.date,
)

properties = create_notion_input_properties(row_input)

create_notion_row(properties)
