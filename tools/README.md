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
- `samples/create_item_similarity_sample_db.py`: Builds a deterministic sample SQLite DB.
- `samples/item_similarity_sample_config.json`: Sample config for the similarity CLI.
- `tests/test_item_name_similarity.py`: `unittest` checks for expected similar records.
- `tests/test_db_column_map.py`: `unittest` checks for DB operation map output.
- `tests/run_tools_tests.py`: Unified test runner for all tools Python tests.
- `validate_story_research_qa.py`: Validates Workflow 6 QA evidence for LLM crawling and OpenClaw coverage.

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

Validate Workflow 6 QA evidence:
```bash
python3 tools/validate_story_research_qa.py --json
```

Or through npm scripts:
```bash
npm run test:tools
```
