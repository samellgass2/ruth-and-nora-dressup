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
- `samples/create_item_similarity_sample_db.py`: Builds a deterministic sample SQLite DB.
- `samples/item_similarity_sample_config.json`: Sample config for the similarity CLI.
- `tests/test_item_name_similarity.py`: Acceptance check for expected similar records.

## Item Similarity Tool
Create the sample DB:
```bash
python3 tools/samples/create_item_similarity_sample_db.py
```

Run similarity scan:
```bash
python3 tools/find_similar_item_names.py --config tools/samples/item_similarity_sample_config.json
```

Run acceptance check:
```bash
python3 tools/tests/test_item_name_similarity.py
```
