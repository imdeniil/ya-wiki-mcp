from ya_wiki_mcp.converter import md_to_yfm


class TestTables:
    def test_simple_table(self):
        md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |"
        result = md_to_yfm(md)
        assert result == "#|\n|| **Name** | **Age** ||\n|| Alice | 30 ||\n|#"

    def test_table_with_alignment(self):
        md = "| Left | Center | Right |\n| :--- | :---: | ---: |\n| a | b | c |"
        result = md_to_yfm(md)
        assert "|| **Left** | **Center** | **Right** ||" in result
        assert "|| a | b | c ||" in result

    def test_multiple_rows(self):
        md = "| H1 | H2 |\n| --- | --- |\n| a | b |\n| c | d |"
        result = md_to_yfm(md)
        assert result.count("||") == 6  # 3 rows * 2 (opening + closing)

    def test_table_surrounded_by_text(self):
        md = "Before\n\n| H |\n| --- |\n| v |\n\nAfter"
        result = md_to_yfm(md)
        assert result.startswith("Before\n\n#|")
        assert result.endswith("|#\n\nAfter")

    def test_no_table(self):
        md = "Just text with a | pipe"
        assert md_to_yfm(md) == md

    def test_pipe_in_text_not_mistaken_for_table(self):
        md = "Use cmd | grep to filter\nNext line"
        assert md_to_yfm(md) == md

    def test_empty_cells(self):
        md = "| H1 | H2 |\n| --- | --- |\n|  |  |"
        result = md_to_yfm(md)
        assert "||  |  ||" in result


class TestCallouts:
    def test_note(self):
        md = "> [!NOTE]\n> This is important"
        result = md_to_yfm(md)
        assert '{% note info "" %}' in result
        assert "This is important" in result
        assert "{% endnote %}" in result

    def test_warning(self):
        md = "> [!WARNING]\n> Be careful"
        result = md_to_yfm(md)
        assert '{% note warning "" %}' in result

    def test_tip(self):
        md = "> [!TIP]\n> Pro tip here"
        result = md_to_yfm(md)
        assert '{% note tip "" %}' in result

    def test_caution(self):
        md = "> [!CAUTION]\n> Danger zone"
        result = md_to_yfm(md)
        assert '{% note alert "" %}' in result

    def test_important(self):
        md = "> [!IMPORTANT]\n> Must read"
        result = md_to_yfm(md)
        assert '{% note warning "" %}' in result

    def test_multiline_callout(self):
        md = "> [!NOTE]\n> Line 1\n> Line 2\n> Line 3"
        result = md_to_yfm(md)
        assert "Line 1\nLine 2\nLine 3" in result

    def test_case_insensitive(self):
        md = "> [!note]\n> Works too"
        result = md_to_yfm(md)
        assert '{% note info "" %}' in result

    def test_regular_blockquote_unchanged(self):
        md = "> Just a regular quote"
        assert md_to_yfm(md) == md


class TestDetails:
    def test_simple_details(self):
        md = "<details><summary>Click me</summary>Hidden content</details>"
        result = md_to_yfm(md)
        assert '{% cut "Click me" %}' in result
        assert "Hidden content" in result
        assert "{% endcut %}" in result

    def test_details_with_whitespace(self):
        md = "<details>\n  <summary>Title</summary>\n  Body here\n</details>"
        result = md_to_yfm(md)
        assert '{% cut "Title" %}' in result
        assert "Body here" in result

    def test_details_with_markdown_inside(self):
        md = "<details><summary>Show code</summary>\n\n```python\nprint('hi')\n```\n\n</details>"
        result = md_to_yfm(md)
        assert '{% cut "Show code" %}' in result
        assert "```python" in result


class TestInlineHTML:
    def test_underline(self):
        assert md_to_yfm("<u>text</u>") == "++text++"

    def test_mark(self):
        assert md_to_yfm("<mark>text</mark>") == "==text=="

    def test_superscript(self):
        assert md_to_yfm("x<sup>2</sup>") == "x2^super^"

    def test_subscript(self):
        assert md_to_yfm("H<sub>2</sub>O") == "H2~sub~O"

    def test_nested_underline_in_sentence(self):
        result = md_to_yfm("This is <u>very important</u> text")
        assert result == "This is ++very important++ text"

    def test_multiple_marks(self):
        result = md_to_yfm("<mark>one</mark> and <mark>two</mark>")
        assert result == "==one== and ==two=="

    def test_multiline_underline(self):
        result = md_to_yfm("<u>line 1\nline 2</u>")
        assert result == "++line 1\nline 2++"


class TestPassthrough:
    """Content that should NOT be modified."""

    def test_plain_text(self):
        text = "Hello world"
        assert md_to_yfm(text) == text

    def test_headings(self):
        text = "# Heading\n## Sub"
        assert md_to_yfm(text) == text

    def test_bold_italic(self):
        text = "**bold** and _italic_"
        assert md_to_yfm(text) == text

    def test_code_blocks(self):
        text = "```python\nprint('hello')\n```"
        assert md_to_yfm(text) == text

    def test_links(self):
        text = "[link](https://example.com)"
        assert md_to_yfm(text) == text

    def test_images(self):
        text = "![alt](image.png)"
        assert md_to_yfm(text) == text

    def test_yfm_native_syntax_unchanged(self):
        text = '{% note info "Title" %}\nContent\n{% endnote %}'
        assert md_to_yfm(text) == text

    def test_empty_string(self):
        assert md_to_yfm("") == ""


class TestCombined:
    """Multiple conversions in one input."""

    def test_table_and_callout(self):
        md = "| H |\n| --- |\n| v |\n\n> [!NOTE]\n> Info"
        result = md_to_yfm(md)
        assert "#|" in result
        assert "{% note info" in result

    def test_details_and_inline_html(self):
        md = "<details><summary>Show</summary><u>underlined</u></details>"
        result = md_to_yfm(md)
        assert '{% cut "Show" %}' in result
        assert "++underlined++" in result

    def test_full_document(self):
        md = """# Title

Some text with <mark>highlight</mark>.

| Name | Role |
| --- | --- |
| Alice | Dev |
| Bob | PM |

> [!WARNING]
> Don't forget!

<details><summary>More info</summary>
Hidden <u>underlined</u> content.
</details>

Regular paragraph."""
        result = md_to_yfm(md)
        assert "# Title" in result
        assert "==highlight==" in result
        assert "#|" in result
        assert "|| **Name** | **Role** ||" in result
        assert '{% note warning "" %}' in result
        assert '{% cut "More info" %}' in result
        assert "++underlined++" in result
        assert "Regular paragraph." in result
