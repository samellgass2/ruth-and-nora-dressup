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
- `ai_news_crawler/requirements.txt`: Pinned Python dependencies for crawler and summarizer workflows.
- `samples/create_item_similarity_sample_db.py`: Builds a deterministic sample SQLite DB.
- `samples/item_similarity_sample_config.json`: Sample config for the similarity CLI.
- `tests/test_item_name_similarity.py`: `unittest` checks for expected similar records.
- `tests/test_db_column_map.py`: `unittest` checks for DB operation map output.
- `tests/run_tools_tests.py`: Unified test runner for all tools Python tests.

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
