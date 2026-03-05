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
