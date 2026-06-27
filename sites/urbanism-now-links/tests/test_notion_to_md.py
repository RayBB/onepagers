"""Tests for notion_to_md.py — pure functions that don't need API access."""

import unittest

from notion_to_md import extract_rich_text, render_blocks


class TestExtractRichText(unittest.TestCase):
    """extract_rich_text handles both dicts and lists."""

    def test_dict_with_rich_text_key(self):
        obj = {"rich_text": [{"plain_text": "Hello world"}, {"plain_text": " foo"}]}
        self.assertEqual(extract_rich_text(obj), "Hello world foo")

    def test_dict_with_title_key(self):
        obj = {"title": [{"plain_text": "Page Title"}]}
        self.assertEqual(extract_rich_text(obj), "Page Title")

    def test_dict_with_text_key(self):
        obj = {"text": [{"plain_text": "Some text content"}]}
        self.assertEqual(extract_rich_text(obj), "Some text content")

    def test_dict_with_caption_key(self):
        obj = {"caption": [{"plain_text": "Image caption"}]}
        self.assertEqual(extract_rich_text(obj), "Image caption")

    def test_dict_prefers_rich_text_over_others(self):
        obj = {
            "rich_text": [{"plain_text": "rich text content"}],
            "title": [{"plain_text": "title content"}],
        }
        self.assertEqual(extract_rich_text(obj), "rich text content")

    def test_dict_no_matching_keys(self):
        obj = {"some_other_key": [{"plain_text": "hello"}]}
        self.assertEqual(extract_rich_text(obj), "")

    def test_dict_empty_rich_text(self):
        obj = {"rich_text": []}
        self.assertEqual(extract_rich_text(obj), "")

    def test_list_directly(self):
        obj = [{"plain_text": "Hello"}, {"plain_text": " world"}]
        self.assertEqual(extract_rich_text(obj), "Hello world")

    def test_list_empty(self):
        self.assertEqual(extract_rich_text([]), "")

    def test_list_with_non_dict_items(self):
        obj = [{"plain_text": "Hello"}, "not a dict"]
        self.assertEqual(extract_rich_text(obj), "Hello")

    def test_plain_string_returns_empty(self):
        self.assertEqual(extract_rich_text("hello"), "")

    def test_none_returns_empty(self):
        self.assertEqual(extract_rich_text(None), "")

    def test_skips_items_without_plain_text(self):
        obj = {"rich_text": [{"type": "mention", "mention": {"type": "user"}}]}
        self.assertEqual(extract_rich_text(obj), "")


class TestRenderBlocks(unittest.TestCase):
    """render_blocks converts Notion block dicts to markdown text."""

    def test_empty_blocks(self):
        self.assertEqual(render_blocks([]), "")

    def test_paragraph(self):
        blocks = [
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "Hello, world!"}]},
            }
        ]
        expected = "Hello, world!"
        self.assertEqual(render_blocks(blocks), expected)

    def test_heading_1(self):
        blocks = [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [{"plain_text": "Title"}]},
            }
        ]
        self.assertEqual(render_blocks(blocks), "# Title")

    def test_heading_2(self):
        blocks = [
            {
                "type": "heading_2",
                "heading_2": {"rich_text": [{"plain_text": "Section"}]},
            }
        ]
        self.assertEqual(render_blocks(blocks), "## Section")

    def test_heading_3(self):
        blocks = [
            {
                "type": "heading_3",
                "heading_3": {"rich_text": [{"plain_text": "Subsection"}]},
            }
        ]
        self.assertEqual(render_blocks(blocks), "### Subsection")

    def test_bulleted_list_item(self):
        blocks = [
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"plain_text": "Item"}]},
            }
        ]
        self.assertEqual(render_blocks(blocks), "- Item")

    def test_numbered_list_item(self):
        blocks = [
            {
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"plain_text": "First"}]},
            }
        ]
        self.assertEqual(render_blocks(blocks), "1. First")

    def test_divider(self):
        blocks = [{"type": "divider", "divider": {}}]
        self.assertEqual(render_blocks(blocks), "---")

    def test_code_block(self):
        blocks = [
            {
                "type": "code",
                "code": {
                    "rich_text": [{"plain_text": "print('hello')"}],
                    "language": "python",
                },
            }
        ]
        expected = "```python\nprint('hello')\n```"
        self.assertEqual(render_blocks(blocks), expected)

    def test_image_no_caption(self):
        blocks = [
            {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": "https://example.com/img.jpg"},
                    "caption": [],
                },
            }
        ]
        self.assertEqual(
            render_blocks(blocks), "[image]  (https://example.com/img.jpg)"
        )

    def test_image_with_caption(self):
        blocks = [
            {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": "https://example.com/img.jpg"},
                    "caption": [{"plain_text": "A nice photo"}],
                },
            }
        ]
        expected = "[image] A nice photo (https://example.com/img.jpg)"
        self.assertEqual(render_blocks(blocks), expected)

    def test_video_block(self):
        blocks = [
            {
                "type": "video",
                "video": {
                    "type": "external",
                    "external": {"url": "https://youtube.com/watch?v=abc"},
                    "caption": [],
                },
            }
        ]
        expected = "[video]  (https://youtube.com/watch?v=abc)"
        self.assertEqual(render_blocks(blocks), expected)

    def test_bookmark(self):
        blocks = [
            {
                "type": "bookmark",
                "bookmark": {"url": "https://example.com"},
            }
        ]
        self.assertEqual(render_blocks(blocks), "https://example.com")

    def test_equation(self):
        blocks = [
            {
                "type": "equation",
                "equation": {"expression": "E = mc^2"},
            }
        ]
        self.assertEqual(render_blocks(blocks), "$E = mc^2$")

    def test_unsupported_block_type_with_text(self):
        """Fallback for unsupported block types that have text."""
        blocks = [
            {
                "type": "toggle",
                "toggle": {"rich_text": [{"plain_text": "Click me"}]},
            }
        ]
        self.assertEqual(render_blocks(blocks), "[toggle] Click me")

    def test_unsupported_block_type_no_text(self):
        """Fallback for unsupported block types without text."""
        blocks = [{"type": "synced_block", "synced_block": {}}]
        self.assertEqual(render_blocks(blocks), "[synced_block]")

    def test_mixed_content_order(self):
        """Paragraphs between list items must be preserved (notion2md bug)."""
        blocks = [
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"plain_text": "Item 1"}]},
            },
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "Description text"}]},
            },
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "Salary is $81k"}]},
            },
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"plain_text": "Item 2"}]},
            },
        ]
        result = render_blocks(blocks)
        self.assertIn("Item 1", result)
        self.assertIn("Description text", result)
        self.assertIn("Salary is $81k", result)
        self.assertIn("Item 2", result)
        # Verify order
        lines = [l for l in result.split("\n") if l.strip()]
        self.assertEqual(lines[0], "- Item 1")
        self.assertEqual(lines[1], "Description text")
        self.assertEqual(lines[2], "Salary is $81k")
        self.assertEqual(lines[3], "- Item 2")

    def test_nested_children(self):
        """Blocks with children should render nested content indented."""
        blocks = [
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"plain_text": "Parent"}]},
                "has_children": True,
                "children": [
                    {
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": [{"plain_text": "Child"}]},
                    }
                ],
            }
        ]
        result = render_blocks(blocks)
        self.assertIn("- Parent", result)
        self.assertIn("  - Child", result)

    def test_multi_level_nesting(self):
        """Three levels of nesting."""
        blocks = [
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"plain_text": "L1"}]},
                "has_children": True,
                "children": [
                    {
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": [{"plain_text": "L2"}]},
                        "has_children": True,
                        "children": [
                            {
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"plain_text": "L3"}]
                                },
                            }
                        ],
                    }
                ],
            }
        ]
        result = render_blocks(blocks)
        lines = [l for l in result.split("\n") if l.strip()]
        self.assertEqual(lines[0], "- L1")
        self.assertEqual(lines[1], "  - L2")
        self.assertEqual(lines[2], "    - L3")

    def test_non_dict_block_skipped(self):
        blocks = [
            "not a dict",
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "real"}]}},
        ]
        self.assertEqual(render_blocks(blocks), "real")  # ty: ignore

    def test_empty_text_paragraph(self):
        blocks = [{"type": "paragraph", "paragraph": {"rich_text": []}}]
        self.assertEqual(render_blocks(blocks), "")

    def test_file_block(self):
        blocks = [
            {
                "type": "file",
                "file": {
                    "type": "external",
                    "external": {"url": "https://example.com/doc.pdf"},
                    "caption": [{"plain_text": "Document"}],
                },
            }
        ]
        expected = "[file] Document (https://example.com/doc.pdf)"
        self.assertEqual(render_blocks(blocks), expected)

    def test_pdf_block(self):
        blocks = [
            {
                "type": "pdf",
                "pdf": {
                    "type": "file",
                    "file": {"url": "https://example.com/report.pdf"},
                    "caption": [],
                },
            }
        ]
        expected = "[pdf]  (https://example.com/report.pdf)"
        self.assertEqual(render_blocks(blocks), expected)

    def test_column_list(self):
        blocks = [{"type": "column_list", "column_list": {}}]
        self.assertEqual(render_blocks(blocks), "[columns]")

    def test_table(self):
        blocks = [{"type": "table", "table": {}}]
        self.assertEqual(render_blocks(blocks), "[table]")

    def test_table_of_contents(self):
        blocks = [{"type": "table_of_contents", "table_of_contents": {}}]
        self.assertEqual(render_blocks(blocks), "[table of contents]")

    def test_breadcrumb(self):
        blocks = [{"type": "breadcrumb", "breadcrumb": {}}]
        self.assertEqual(render_blocks(blocks), "[breadcrumb]")

    def test_embed(self):
        blocks = [{"type": "embed", "embed": {"url": "https://example.com/map"}}]
        self.assertEqual(render_blocks(blocks), "https://example.com/map")

    def test_link_preview(self):
        blocks = [
            {"type": "link_preview", "link_preview": {"url": "https://example.com"}}
        ]
        self.assertEqual(render_blocks(blocks), "https://example.com")


class TestRenderBlocksEdgeCases(unittest.TestCase):
    """Edge cases and error resilience."""

    def test_block_missing_type_field(self):
        blocks = [{"paragraph": {"rich_text": [{"plain_text": "text"}]}}]
        # No "type" key — empty string fallback, nothing rendered
        self.assertEqual(render_blocks(blocks), "")

    def test_block_type_value_is_wrong_type(self):
        blocks = [{"type": 123, "123": {"rich_text": [{"plain_text": "weird"}]}}]
        # type is an int — falls to generic handler with btype="123" from str fallback
        # Actually block.get("type", "") returns 123, which is truthy, so renders "[123]"
        result = render_blocks(blocks)
        self.assertEqual(result, "[123]")

    def test_mixed_list_in_blocks(self):
        blocks = [
            None,
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "A"}]}},
            [1, 2, 3],
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "B"}]}},
        ]
        self.assertEqual(render_blocks(blocks), "A\nB")  # ty: ignore

    def test_caption_direct_list(self):
        """caption as a list (not wrapped in a dict)."""
        # This tests the fix where extract_rich_text accepts a list
        blocks = [
            {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": "https://example.com/img.jpg"},
                    "caption": [{"plain_text": "Direct list caption"}],
                },
            }
        ]
        result = render_blocks(blocks)
        self.assertIn("Direct list caption", result)

    def test_blank_paragraphs(self):
        blocks = [
            {"type": "paragraph", "paragraph": {"rich_text": []}},
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": " "}]}},
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Text"}]}},
        ]
        self.assertEqual(render_blocks(blocks), "\n\nText")


if __name__ == "__main__":
    unittest.main()
