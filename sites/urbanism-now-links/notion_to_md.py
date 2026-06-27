from notion_client import Client


def extract_rich_text(obj) -> str:
    """Extract plain text from a Notion block/property value.

    Handles both: a dict (with rich_text/title/text/caption keys) or
    a list (a rich_text array directly, e.g. from caption/heading).
    """
    if isinstance(obj, list):
        return "".join(t.get("plain_text", "") for t in obj if isinstance(t, dict))
    if not isinstance(obj, dict):
        return ""
    for key in ("rich_text", "title", "text", "caption"):
        items = obj.get(key, [])
        if isinstance(items, list):
            parts = [t.get("plain_text", "") for t in items if isinstance(t, dict)]
            if parts:
                return "".join(parts)
    return ""


def render_blocks(blocks: list[dict], indent: int = 0) -> str:
    """Render Notion block dicts to markdown-like text.

    Args:
        blocks: Already-fetched Notion block dicts from the API.
        indent: Indentation level for nested blocks.

    Returns:
        Markdown-like text representation of the blocks.
    """
    lines = []
    prefix = "  " * indent
    for block in blocks:
        if not isinstance(block, dict):
            continue
        btype = block.get("type", "")
        obj = block.get(btype, {})
        if not isinstance(obj, dict):
            obj = {}
        text = extract_rich_text(obj)

        if btype in ("paragraph", "quote", "callout"):
            lines.append(f"{prefix}{text}" if text.strip() else "")
        elif btype in ("heading_1",):
            lines.append(f"{prefix}# {text}" if text else "")
        elif btype in ("heading_2",):
            lines.append(f"{prefix}## {text}" if text else "")
        elif btype in ("heading_3",):
            lines.append(f"{prefix}### {text}" if text else "")
        elif btype in ("bulleted_list_item", "numbered_list_item", "to_do"):
            marker = (
                "-"
                if btype == "bulleted_list_item"
                else ("1." if btype == "numbered_list_item" else "-")
            )
            lines.append(f"{prefix}{marker} {text}" if text else f"{prefix}{marker}")
        elif btype == "divider":
            lines.append(f"{prefix}---")
        elif btype == "code":
            lang = obj.get("language", "")
            lines.append(f"{prefix}```{lang}")
            lines.append(f"{prefix}{text}")
            lines.append(f"{prefix}```")
        elif btype in ("image", "video", "file", "pdf"):
            caption = extract_rich_text(
                obj.get("caption", [{}]) if isinstance(obj, dict) else {}
            )
            url = obj.get("external", {}).get("url", "") or obj.get("file", {}).get(
                "url", ""
            )
            lines.append(
                f"{prefix}[{btype}] {caption}{' (' + url + ')' if url else ''}"
            )
        elif btype == "bookmark":
            lines.append(f"{prefix}{obj.get('url', '')}")
        elif btype == "equation":
            lines.append(f"{prefix}${obj.get('expression', '')}$")
        elif btype == "table":
            lines.append(f"{prefix}[table]")
        elif btype == "column_list":
            lines.append(f"{prefix}[columns]")
        elif btype in ("embed", "link_preview"):
            lines.append(f"{prefix}{obj.get('url', '')}")
        elif btype == "table_of_contents":
            lines.append(f"{prefix}[table of contents]")
        elif btype == "breadcrumb":
            lines.append(f"{prefix}[breadcrumb]")
        elif btype and text:
            lines.append(f"{prefix}[{btype}] {text}")
        elif btype:
            lines.append(f"{prefix}[{btype}]")

        children = block.get("children") if isinstance(block, dict) else None
        if isinstance(children, list) and children:
            child_text = render_blocks(children, indent + 1)
            if child_text:
                lines.append(child_text)

    return "\n".join(lines)


def _inline_child_blocks(block: dict, notion: Client) -> dict:
    """Recursively fetch and inline child blocks into a block dict."""
    if not isinstance(block, dict):
        return block
    if block.get("has_children"):
        try:
            resp = notion.blocks.children.list(block["id"])
            children = resp.get("results", [])  # ty: ignore
            if isinstance(children, list):
                for child in children:
                    _inline_child_blocks(child, notion)
                block["children"] = children
        except Exception:
            pass
    return block


def get_page_body_as_md(page_id: str, notion: Client) -> str:
    """Fetch a Notion page's body blocks and render them as markdown.

    Uses the Notion API directly (not notion2md) to render all block types,
    including paragraphs that appear between list items (notion2md drops these).
    """
    try:
        resp = notion.blocks.children.list(page_id)
        top_blocks = resp.get("results", [])  # ty: ignore
        if not isinstance(top_blocks, list):
            return ""
        for block in top_blocks:
            _inline_child_blocks(block, notion)
        return render_blocks(top_blocks)
    except Exception as e:
        print(f"  [notion_to_md] error getting page body: {e}")
        return ""
