# Contributing

Thanks for improving SwiftFilez.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
```

## Before opening a PR

Run the same core checks used by CI:

```bash
python -m compileall -q swift_files main.py
python -m pytest -q
python main.py --version
python main.py doctor --json
```

Or use:

```bash
make test
make smoke
```

## Design expectations

- Keep domain logic independent of Rich/Typer rendering where practical.
- Prefer `--json` output for commands useful in automation.
- Use exit code `2` for a successfully evaluated policy/integrity violation and exit code `1` for operational errors.
- Destructive operations must be explicit, recoverable where possible, and documented.
- Add tests for new file formats and failure paths.
- Update README and architecture docs when the command surface, environment variables, container behavior, or operational semantics change.

## Pull requests

Keep PRs focused, explain the operational impact, and include validation results. CI runs the Python matrix, package build, and container build before changes should be merged.
