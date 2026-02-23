import os
from typing import List, Optional

import instructor
from dotenv import load_dotenv
from litellm import completion
from pydantic import BaseModel, Field, field_validator

from notion import get_select_options
from scrape_page import ExtractedPage

load_dotenv()

MODEL = os.environ.get("LITELLM_MODEL", "zai/glm-4.7")

# Set Z.AI coding endpoint for coding plan users
ZAI_CODING_API_BASE = "https://api.z.ai/api/coding/paas/v4"

# Create instructor client using litellm integration
client = instructor.from_litellm(completion, mode=instructor.Mode.MD_JSON)

# Map Python field names to Notion property names
FIELD_TO_NOTION = {
    "vibe": "Vibe",
    "region": "Region",
    "topics": "Topic",
    "other_tags": "Other Tags",
}

SUMMARY_PROMPT = """
You are the writer for an urbanism newsletter that goes out to many subscribers each week.
Your job is to take article and pull out the most interesting and important information from them to include in the newsletter.
You can assume your audience is already mildly familair with urbanism issues and wants to know about new developments and have leads for new ideas to explore.
More than informing, you seek to inspire and spark action.

Write a 1-2 sentence summary of the content following the AP style.
Start with the most important information to make it easy to scan.
The target audience is people who are interested in urbanism.
Don't be afraid of jargon but focus on clarity.
If there is a salary include it toward the end In the format of "$Xk - $Yk salary.".
If there is a deadline include it at the end in this format: "March 24." Only include the month and day.
If there is a job title make it lower case, following AP style.
Examples for different types of content:
Article: A 21-year-old, with the help of the Tufi Association, created a public transport app for his hometown in Morocco. He single-handedly mapped Tétouan's entire public transport network and became one of the top four mappers in the country.
Job: NACTO is hiring a senior manager, multimodal design and programs to work on street design and technical projects. $99k - $109k salary. Apply by March 24.
Event: The Pattis Family Foundation Global Cities Book Award, in partnership with Metropolis, is offering a $25,000 prize for a non-fiction book published in English between January 2023 and March 2025 that focuses on how cities tackle global challenges. March 31.
"""


class LLM_Results(BaseModel):
    """Pydantic model for LLM categorization results with dynamic enum support."""

    vibe: Optional[str] = Field(
        description=f"Is this content about something positive people want to see more of in the world or negative that people want less of in the world? Choose from: {', '.join(get_select_options('Vibe'))}"
    )
    region: Optional[str] = Field(
        description=f"The region that this content is about. If it doesn't specify, where does it originate from? Choose from: {', '.join(get_select_options('Region'))}"
    )
    topics: List[str] = Field(
        description=f"The topics that best map to this content. Choose from: {', '.join(get_select_options('Topic'))}"
    )
    other_tags: List[str] = Field(
        default_factory=list,
        description=f"Optional tags. Choose from: {', '.join(get_select_options('Other Tags'))}",
    )
    summary: str = Field(description=SUMMARY_PROMPT)
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None

    # Single validator for all single-value enum fields
    @field_validator("vibe", "region", mode="before")
    def validate_single_enum(v, info):
        """Validate single-value enum fields (vibe, region)."""
        if v is None:
            return v
        notion_name = FIELD_TO_NOTION[info.field_name]
        valid_options = get_select_options(notion_name)
        return v if v in valid_options else valid_options[0]

    # Single validator for all list enum fields
    @field_validator("topics", "other_tags", mode="before")
    def validate_list_enum(v, info):
        """Validate list enum fields (topics, other_tags)."""
        notion_name = FIELD_TO_NOTION[info.field_name]
        valid_options = get_select_options(notion_name)
        return [tag if tag in valid_options else valid_options[0] for tag in v]


def get_llm_categorizations(
    page: ExtractedPage,
) -> LLM_Results:
    """Extract structured categorizations using Instructor."""
    kwargs = {}

    # Use coding endpoint for Z.AI models (for coding plan users)
    if MODEL.startswith("zai/"):
        kwargs["api_base"] = ZAI_CODING_API_BASE

    result = client.create(
        model=MODEL,
        response_model=LLM_Results,
        messages=[
            {
                "role": "user",
                "content": f"Url: {page.url}\nTitle: {page.title}\nText: {page.text}\nFill out the information about the above content",
            }
        ],
        **kwargs,  # Pass api_base for Z.AI coding plan
    )
    return result


if __name__ == "__main__":
    page = ExtractedPage(
        url="https://www.archpaper.com/2026/02/curbed-archive-urban-reporting-goes-dark/",
        title="Curbed’s archive of urban reporting goes dark",
        text="Vox Media has taken down a significant portion of Curbed’s archive of urban reporting, leaving thousands of historic stories about city evolution, architecture, and real estate inaccessible. The decision, attributed to a content management system migration, has drawn criticism from former staffers and urbanism advocates who lament the loss of crucial historical documentation and civic memory.",
    )
    print(get_llm_categorizations(page))
