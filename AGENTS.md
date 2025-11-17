# Repository Guidelines

在整个协作过程中请使用中文交流，确保讨论和文档保持一致的语言环境。

## Project Structure & Module Organization
Service code lives in `src/harmony_tools/`; `mcp_service.py` registers every FastMCP tool while `hdc_runner.py` centralizes `hdc` subprocess logic and `hvigor_runner.py` mirrors that behavior for hvigor builds. Project metadata and the `harmony-hdc-mcp` console script wiring sit in `pyproject.toml` and `uv.lock`. FastMCP setup notes live under `python-sdk/`; treat it as upstream reference.

## Build, Test, and Development Commands
- `uv pip install -e .` installs the package in editable mode and exposes the `harmony-hdc-mcp` console script.
- `HDC_PATH=$HOME/ohos-sdk/tools/hdc uv run harmony-hdc-mcp` starts the MCP server while pointing at a specific hdc binary.
- `uv run python -m harmony_tools.mcp_service` mirrors the console script and is helpful when debugging with breakpoints.
- `uv run pytest tests` is the expected automated test command once suites are added; use `PYTEST_DISABLE_PLUGIN_AUTOLOAD=""` when plugins interfere.
- `HVIGORW_PATH=/path/to/hvigorw uv run harmony-hdc-mcp` ensures the `hvigor_build` tool resolves a custom wrapper when your project lacks an executable `./hvigorw`.

## Coding Style & Naming Conventions
Target Python 3.11+, use four-space indents, and preserve typed signatures (every public function already carries annotations). Keep public APIs in `snake_case`, classes in `PascalCase`, constants uppercased (`HDC_PATH`), and prefer dataclasses for structured payloads. Module docstrings should summarize the MCP tool they expose, wrap text near 100 characters, and borrow CLI example tone from `README.md`. Run `ruff` (or another PEP 8 checker) before opening a PR if it is available in your environment.

## Testing Guidelines
Place tests under `tests/` mirroring package paths (e.g., `tests/test_hdc_runner.py`) and name them `test_<behavior>`. Focus on result serialization (`as_dict`), argument parsing (`_split_arguments`), and timeout/device-edge cases by stubbing `subprocess.run`. Guard live-device suites with markers such as `@pytest.mark.slow` so CI can skip them. Before shipping, run `uv run pytest` and a manual smoke test like `uv run harmony-hdc-mcp` followed by `list_targets`.

## Commit & Pull Request Guidelines
History is not distributed with this snapshot, so default to conventional commits (`feat: add uitest timeout guard`) with a 72-character imperative subject. Each PR should explain the user-visible change, list verification commands, attach screenshots or logs when tool output changes, and link any tracking issues. Keep diffs scoped to one MCP concern, mention the affected tools in the title, and update docs (README or this guide) when behavior shifts.

## Security & Configuration Tips
Never hard-code device identifiers or credentials; rely on the `device` argument passed through MCP and prefer env vars for sensitive paths. Avoid logging entire `stdout`/`stderr` for privileged commands—trim or redact before surfacing in responses, and use env toggles (`HDC_PATH`, `UV_CACHE_DIR`) instead of editing scripts for custom toolchains.
