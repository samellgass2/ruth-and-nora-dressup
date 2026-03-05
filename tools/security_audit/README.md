# Security Audit Tools

## Directory Structure Mapper

Maps a repository into a deterministic directory tree for audit workflows.

Run as CLI:

```bash
python3 tools/security_audit/map_directory_structure.py --root .
```

JSON output:

```bash
python3 tools/security_audit/map_directory_structure.py --root . --json
```

Python API:

```python
from pathlib import Path
from tools.security_audit.directory_structure_mapper import map_directory_structure

directory_map = map_directory_structure(Path('.'))
print(directory_map.total_directories, directory_map.total_files)
```

Behavior notes:
- Hidden paths are excluded by default.
- Common build/cache directories such as `node_modules` are excluded by default.
- Raises `DirectoryAccessError` when traversal cannot access a directory.

## Function Call Relationship Mapper

Builds a deterministic function call graph for Python files in a repository.

Run as CLI:

```bash
python3 tools/security_audit/map_function_calls.py --root .
```

JSON output:

```bash
python3 tools/security_audit/map_function_calls.py --root . --json
```

Python API:

```python
from pathlib import Path
from tools.security_audit.function_call_relationship_mapper import (
    map_function_call_relationships,
)

call_map = map_function_call_relationships(Path("."))
print(call_map.function_count, call_map.relation_count)
```

Behavior notes:
- Hidden paths are excluded by default.
- Common build/cache directories such as `node_modules` are excluded by default.
- Raises `FileParseError` if any scanned Python file cannot be parsed.

## Security Audit Report Generator

Builds a consolidated report from directory and function-call maps.

Run as CLI:

```bash
python3 tools/security_audit/generate_security_audit_report.py --root .
```

Write Markdown report to file:

```bash
python3 tools/security_audit/generate_security_audit_report.py --root . --output SECURITY_AUDIT_REPORT.md
```

JSON output:

```bash
python3 tools/security_audit/generate_security_audit_report.py --root . --json
```

Python API:

```python
from pathlib import Path
from tools.security_audit.security_audit_report_generator import (
    generate_security_audit_report,
)

report = generate_security_audit_report(Path("."))
print(report.summary.high_findings, report.summary.medium_findings)
```
