# Tools Directory

This directory contains project tooling assets used to support development and automation tasks.

## Purpose
- Keep utility scripts and helper documents grouped in one place.
- Provide a predictable location for future tool-specific docs and resources.

## Current Contents
- `README.md`: Base overview for the `tools` directory.
- `DESIGN.md`: Base design document for tooling behavior and conventions.
- `.gitkeep`: Placeholder to keep the directory tracked when empty.
- `find_similar_item_names.py`: CLI that reads DB config and finds similar item names.
- `generate_db_column_map.py`: CLI that runs a DB column operation and returns map-like output.
- `setup_ai_news_env.py`: Bootstraps a local Python virtualenv for AI news crawling/summarization dependencies and verifies with `pip freeze`.
- `setup_security_audit_env.py`: Bootstraps a local Python virtualenv for security audit tool dependencies and verifies with `pip freeze`.
- `shared/mock_ai_service.py`: Shared deterministic mock AI service used by AI-news summarization tooling.
- `ai_news_crawler/requirements.txt`: Pinned Python dependencies for crawler and summarizer workflows.
- `security_audit/requirements.txt`: Pinned Python dependencies for security audit workflow.
- `security_audit/directory_structure_mapper.py`: Callable API to map a repository directory tree with deterministic ordering.
- `security_audit/map_directory_structure.py`: CLI wrapper for directory-structure mapping output in text or JSON.
- `security_audit/function_call_relationship_mapper.py`: Callable API to parse Python files and map function-call relationships.
- `security_audit/map_function_calls.py`: CLI wrapper for function-call relationship mapping output in text or JSON.
- `security_audit/security_audit_report_generator.py`: Callable API to generate security findings from mapping outputs.
- `security_audit/generate_security_audit_report.py`: CLI wrapper for Markdown/JSON security-audit report generation.
- `security_audit/README.md`: Usage notes for security-audit mapping tools.
- `tests/test_security_audit_directory_mapper.py`: `unittest` checks for expected directory-map behavior and repository structure output.
- `tests/test_security_audit_function_call_mapper.py`: `unittest` checks for expected function-call mapping behavior and parse-failure handling.
- `tests/test_security_audit_report_generator.py`: `unittest` checks for report findings, actionable fixes, and CLI output.
- `ai_news_crawler/sources.json`: Default source list with Arxiv and additional AI news websites.
- `ai_news_crawler/article_retriever.py`: Retrieval/parsing module for Arxiv, RSS, and HTML sources.
- `ai_news_crawler/retrieve_articles.py`: CLI to crawl configured sources and emit normalized JSON.
- `ai_news_crawler/newsletter_summarizer.py`: Summarization and deterministic HTML newsletter rendering module.
- `ai_news_crawler/summarize_articles.py`: CLI to summarize retrieved articles and write newsletter HTML output.
- `samples/create_item_similarity_sample_db.py`: Builds a deterministic sample SQLite DB.
- `samples/item_similarity_sample_config.json`: Sample config for the similarity CLI.
- `tests/test_item_name_similarity.py`: `unittest` checks for expected similar records.
- `tests/test_db_column_map.py`: `unittest` checks for DB operation map output.
- `tests/test_ai_news_article_retriever.py`: `unittest` checks article retrieval and source config parsing.
- `tests/run_tools_tests.py`: Unified test runner for all tools Python tests.

## Unified Python Tool Setup
Use the repository Bash setup script to configure both tool environments and
create local executable shims:
```bash
bash scripts/setup_python_tools.sh
```

Verify only (no package reinstall):
```bash
bash scripts/setup_python_tools.sh --verify-only
```

By default, shims are created in `.tools-bin`. Add them to `PATH`:
```bash
export PATH="$PWD/.tools-bin:$PATH"
```

## Item Similarity Tool
Create the sample DB:
```bash
python3 tools/samples/create_item_similarity_sample_db.py
```

Run similarity scan:
```bash
python3 tools/find_similar_item_names.py --config tools/samples/item_similarity_sample_config.json
```

Run DB operation map tool:
```bash
python3 tools/generate_db_column_map.py --database tools/samples/item_similarity_sample.db --table items --column is_active --operation value_counts --json
```

Run tools test suite:
```bash
python3 tools/tests/run_tools_tests.py
```

Or through npm scripts:
```bash
npm run test:tools
```

## AI News Crawler Environment
Create or update a local crawler/summarizer virtualenv:
```bash
npm run setup:ai-news-env
```

Verify required packages via `pip freeze` (without reinstalling):
```bash
npm run verify:ai-news-env
```

Default venv location is `.venv-ai-news`. To use a custom location:
```bash
python3 tools/setup_ai_news_env.py --venv .venv-custom-name
```

## Security Audit Environment
Create or update a local security-audit virtualenv:
```bash
npm run setup:security-audit-env
```

Verify required packages via `pip freeze` (without reinstalling):
```bash
npm run verify:security-audit-env
```

Map the current repository structure (text tree):
```bash
python3 tools/security_audit/map_directory_structure.py --root .
```

Map as JSON with top-level only:
```bash
python3 tools/security_audit/map_directory_structure.py --root . --json --max-depth 0
```

Map Python function-call relationships:
```bash
python3 tools/security_audit/map_function_calls.py --root .
```

Map function-call relationships as JSON:
```bash
python3 tools/security_audit/map_function_calls.py --root . --json
```

Generate a security audit report:
```bash
python3 tools/security_audit/generate_security_audit_report.py --root .
```

Write the report to a markdown file:
```bash
python3 tools/security_audit/generate_security_audit_report.py --root . --output SECURITY_AUDIT_REPORT.md
```

Default venv location is `.venv-security-audit`. To use a custom location:
```bash
python3 tools/setup_security_audit_env.py --venv .venv-custom-name
```

Retrieve articles from default configured sources:
```bash
python3 tools/ai_news_crawler/retrieve_articles.py --pretty
```

Use a custom source config:
```bash
python3 tools/ai_news_crawler/retrieve_articles.py --config path/to/sources.json --pretty
```

Generate newsletter HTML from live retrieval:
```bash
python3 tools/ai_news_crawler/summarize_articles.py --title "AI News Digest"
```

Generate newsletter HTML from a saved retrieval JSON:
```bash
python3 tools/ai_news_crawler/summarize_articles.py --input-json retrieved.json --output-html newsletter.html --print-html
```
