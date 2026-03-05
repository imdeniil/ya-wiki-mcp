# Yandex Wiki Markup (YFM) Syntax Reference

## Inline Formatting

| Markup | Result |
|--------|--------|
| `**text**` | Bold |
| `_text_` | Italic |
| `++text++` | Underlined |
| `~~text~~` | Strikethrough |
| `##text##` | Monospace |
| `==text==` | Highlighted |
| `{color}(text)` | Colored text (gray/yellow/orange/red/green/blue/violet) |
| `text^super^` | Superscript |
| `text~sub~` | Subscript |

Combine: `**_bold italic_**`, `{orange}(~~strikethrough orange~~)`

## Headings

```
# H1
## H2
### H3
#### H4
##### H5
###### H6
##+ Collapsible H2
#### Heading with anchor {#my-anchor}
```

## Lists

Numbered (all items use `1.`, sub-items indented 3 spaces):
```
1. First
1. Second
   1. Sub-item
```

Bulleted (`*`, `-`, or `+`, sub-items indented 2 spaces):
```
* Item
  * Sub-item
```

Checkbox (blank line between items):
```
[ ] Unchecked

[x] Checked
```

## Code

Inline: `` `code` ``

Block:
````
```python
print("hello")
```
````

## Math (LaTeX)

Inline: `$e^{ix}=\cos x+i\sin x$`

Block:
```
$$
\sum_{i=1}^n x_i
$$
```

## Links

```
[text](https://url.com)
[text](/wiki/page/path)
[text](../relative/path/#anchor)
[text](#local-anchor)
[text](mailto:email@example.com)
```

Tracker issues auto-link: `TEST-123`. Escape with backticks: `` `TEST-123` ``

## Images

```
![alt](url)
![alt](url "caption" =300x200)
[![alt](img_url)](link_url)
```

## Tables

Wiki-style (supports multi-line cells and markup inside):
```
#|
|| **Header 1** | **Header 2** ||
|| cell 1 | cell 2 ||
|#
```

Markdown-style:
```
| H1 | H2 | H3 |
| :--- | :----: | ---: |
| left | center | right |
```

## Notes

```
{% note info "Title" %}
Content
{% endnote %}
```

Types: `info` (blue), `warning` (orange), `alert` (red), `tip` (green).

## Collapsible Sections (Cut)

```
{% cut "Click to expand" %}
Hidden content here
{% endcut %}
```

## Tabs

```
{% list tabs %}
- Tab 1 title
    Tab 1 content
- Tab 2 title
    Tab 2 content
{% endlist %}
```

## Blockquotes

```
> Quote
>> Nested quote
```

## Blocks and Layouts

```
{% block align=center width=1000 padding=xs border=solid borderSize=m borderColor=warning %}
Block content
{% endblock %}

{% layout gap=l cols=auto justify=start %}
{% block col=3 %}Cell 1{% endblock %}
{% block col=7 %}Cell 2{% endblock %}
{% endlayout %}
```

## Table of Contents

```
{% toc page="/path/to/page" from="h1" to="h6" %}
```

## Page Tree

```
{% tree page="/section" depth="5" sort="asc" sort_by="title" %}
```

sort_by: `title`, `created_at`, `modified_at`

## Include Content from Another Page

```
{% include page="/users/name/page" warning="false" from="a1" to="a2" %}
```

## File Attachment

```
{% file src="/path/to/file.zip" name="file.zip" type="application/zip" %}
```

## Dynamic Table (Grid) Embed

```
{% wgrid id="UUID" %}
{% wgrid id="UUID" readonly="1" num="1" sort="0" columns="name, description" %}
{% wgrid id="UUID" filter="[name]=<value>, [status]!=done" %}
```

Filter operators: `=`, `!=`, `<`, `>`, `<=`, `>=`, `~` (contains), `!~`, `between ... and ...`, `in (...)`, `not in (...)`

## Diagrams

Mermaid:
````
```mermaid
sequenceDiagram
    Alice->>Bob: Hello
```
````

PlantUML:
```
{% diagram %}
@startuml
Bob->Alice: Hello
@enduml
{% enddiagram %}
```

## iframe

```
/iframe/(src="https://example.com" width="300" height="100" frameborder="0" scrolling="yes")
```

Allowed domains: yandex.ru, youtube.com, vimeo.com, vk.com, rutube.ru, coub.com, etc.

## HTML Block

```
::: html

<h1>Heading</h1>
<p>Content</p>

:::
```

## Miscellaneous

| Syntax | Effect |
|--------|--------|
| `@login` | User mention |
| `---` or `****` or `____` | Horizontal rule |
| `:emoji:` | Emoji shortcode |
| `\` before char | Escape markup |
| `[//]: # (text)` | Hidden comment (visible to editors only) |
