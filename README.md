# ruth-and-nora-dressup

Dress-up prototype for Ruth and Nora built with React, TypeScript, Vite, and PixiJS.

The repository contains two primary tracks:

- Runtime app code for sprite animation and item equip interactions.
- Project-side tooling under `tools/` for SQLite checks and data-quality style utilities.

## Stack

- React 18
- TypeScript 5
- Vite 7
- PixiJS 7 (`pixi.js`) + `@pixi/react`
- Python 3 tools for utility scripts and test harnesses

## Quick Start

Install dependencies:

```bash
npm install
```

Start development server:

```bash
npm run dev
```

Build production bundle:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

Run TypeScript checks:

```bash
npm run typecheck
```

## App Features (Current)

- Loads pixelized atlases for Ruth and Nora.
- Splits animation into `idle` and `action` sequences.
- Auto-runs action animation after idle-loop intervals.
- Supports character switching.
- Supports inventory equip/unequip by slot.
- Renders equipped item overlays on character sprites.

## Tools Directory Overview

Location: `tools/`

The tools directory contains utility scripts and tests intended for local developer workflows.

### Current Tooling Files

- `tools/find_similar_item_names.py`
  - Reads a config file and reports similar item names from SQLite data.
- `tools/generate_db_column_map.py`
  - Runs a DB column operation (for example value counts) and outputs map-style results.
- `tools/samples/create_item_similarity_sample_db.py`
  - Creates deterministic sample SQLite data for tooling tests.
- `tools/samples/item_similarity_sample_config.json`
  - Sample config consumed by similarity tool.
- `tools/tests/test_item_name_similarity.py`
  - Unit tests for similarity matching behavior.
- `tools/tests/test_db_column_map.py`
  - Unit tests for column-map generation behavior.
- `tools/tests/run_tools_tests.py`
  - Unified test runner for tooling tests.
- `tools/README.md`
  - Tool-specific usage and command examples.
- `tools/DESIGN.md`
  - Tooling design constraints and conventions.

## Tools Quickstart

Create sample DB:

```bash
python3 tools/samples/create_item_similarity_sample_db.py
```

Run similarity scan:

```bash
python3 tools/find_similar_item_names.py --config tools/samples/item_similarity_sample_config.json
```

Run DB column map command:

```bash
python3 tools/generate_db_column_map.py --database tools/samples/item_similarity_sample.db --table items --column is_active --operation value_counts --json
```

Run tools test suite:

```bash
npm run test:tools
```

Validate Workflow 6 QA evidence:

```bash
python3 tools/validate_story_research_qa.py --json
```

## Sprite Pipeline

Regenerate pixelized runtime atlases from source repacked sheets:

```bash
npm run generate:sprites
```

Source assets:

- `src/sprites/ruth_sheet_repacked.png`
- `src/sprites/ruth_sheet_repacked.json`
- `src/sprites/nora_sheet_repacked.png`
- `src/sprites/nora_sheet_repacked.json`

Pipeline script:

- `scripts/generate_pixel_atlases.py`

Generated runtime output:

- `public/sprites/*`

## Project Layout

- `src/` - React + Pixi app source.
- `public/` - runtime-served atlases and item textures.
- `scripts/` - sprite generation pipeline scripts.
- `tools/` - developer utility scripts, sample DB assets, tests, and tooling docs.
- `research/` - workflow research artifacts.

## Notes

- Keep `public/` atlases generated and in sync with source sprites.
- Keep tool scripts deterministic and covered by `tools/tests` when behavior changes.
- Prefer updating `tools/README.md` and root `README.md` together when tooling commands change.

## Workflow 6 QA Coverage (Task 66)

The QA block for Workflow 6 is resolved with explicit, source-backed answers for:

- LLM-based crawling implementation/evidence.
- OpenClaw story coverage.

Evidence artifacts:

- `research/workflow-6-qa-evidence.md`
- `research/workflow-6-qa-evidence.json`

Automated validator:

- `tools/validate_story_research_qa.py`
