# Общие правила

Думай и действуй на английском, отвечай в чате на русском.
mcp.txt - Не читай полностью ищи в нем необходимую информацию, это fastmcp докумнетация на случай если нужно будет что-то уточнить
yandex-wiki-api.md - апи для wiki
Используй uv

# Архитектура

- `client.py` — тонкая обёртка над `ya-wiki-api` (AsyncWikiClient). Создаёт клиент из env vars.
- `server.py` — FastMCP сервер, 36 тулов. Использует `wiki.pages.*` / `wiki.grids.*` напрямую.
- `tree_manager.py` — кэш дерева страниц в `tree.yaml`. Авто-обновляется при create/update/delete/clone.
- `converter.py` — Markdown → YFM конвертер.
- `prompt_manager.py` — шаблоны промптов из `.md` файлов с YAML frontmatter.

# Зависимости

ya-wiki-api >= 0.2.0 (HTTP клиент для Yandex Wiki API)
fastmcp >= 2.0.0 (MCP сервер)
