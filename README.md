<h1 align="center">
  <img alt="SwiftFilez logo" src="/assets/file.gif" width="224px"/><br/>
  SwiftFilez
</h1>

<p align="center"><strong>Safe file and artifact operations for humans, scripts, and CI pipelines.</strong></p>

SwiftFilez (`swf`) is a production-minded CLI for inspecting files, generating integrity manifests, detecting drift, finding duplicate artifacts, validating CSV data, and extracting content from DOCX/PDF files.

It started as a file-manipulation prototype. The current design deliberately adds the concerns that matter in platform tooling: deterministic automation interfaces, non-zero policy-gate exit codes, cryptographic integrity, concurrency, safe mutation defaults, container packaging, and CI validation.

## Why this is a Platform Engineering project

SwiftFilez demonstrates patterns used in internal developer platforms and build/release tooling:

- **Artifact integrity** — SHA-256 by default, versioned manifests, and drift verification.
- **Automation contracts** — machine-readable `--json` output on operational commands.
- **Policy gates** — manifest and CSV validation return exit code `2` when policy fails.
- **Safety-first mutations** — duplicate cleanup is dry-run by default and quarantines instead of deleting.
- **Concurrency** — directory scans and duplicate hashing use a bounded worker pool.
- **Configuration via environment** — no hard-coded workstation assumptions.
- **Packaging** — installable `swf` / `swiftfilez` console commands.
- **Containers** — non-root Docker image with a persistent working volume.
- **CI/CD** — multi-version Python tests, package build, and container smoke test.
- **Diagnostics** — `swf doctor` provides an operational self-check.

See [docs/PLATFORM_ENGINEERING.md](docs/PLATFORM_ENGINEERING.md) for the design rationale and failure model.

## General artifact operations

```bash
swf inspect ./release.tar.gz
swf hash ./release.tar.gz --algorithm sha512
swf scan ./dist
swf duplicates ./artifacts
swf duplicates ./artifacts --apply --quarantine-dir ./quarantine
```

`duplicates` never deletes files. Without `--apply`, it only reports what would move.

## Integrity manifests and drift detection

```bash
swf manifest build ./dist --output release-manifest.json
swf manifest verify release-manifest.json --root ./dist --strict
swf manifest verify release-manifest.json --root ./dist --strict --json
```

A clean verification exits `0`; integrity drift exits `2`, making the command useful as a release/deployment policy gate.

## CSV operations

```bash
swf csv inspect customers.csv
swf csv duplicates customers.csv --key customer_id
swf csv dedupe customers.csv --key customer_id --output customers-clean.csv
swf csv sort customers.csv --column customer --output customers-sorted.csv
swf csv validate customers.csv --required customer_id --required status
```

The original project's credit/debit report idea is now a working generic grouped summary:

```bash
swf csv summarize ledger.csv \
  --group-by customer \
  --sum credit \
  --sum debit
```

## DOCX operations

```bash
swf docx inspect runbook.docx
swf docx extract runbook.docx --output runbook.txt
swf docx copy runbook.docx --output backup/runbook.docx
```

Inspection reports paragraph/table/word counts and core metadata. Extraction includes table text.

## PDF operations

```bash
swf pdf inspect architecture.pdf
swf pdf extract architecture.pdf --output architecture.txt
swf pdf copy architecture.pdf --output backup/architecture.pdf
```

Encrypted PDFs can be inspected/extracted with `--password`.

> The old README listed PDF signing as a TODO. SwiftFilez no longer advertises signing because it was never implemented. The supported command surface is intentionally limited to functionality that actually works and is tested.

## Install

Python 3.10+ is required.

```bash
git clone https://github.com/mergemaven11/swift.git
cd swift
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install:

```bash
python -m pip install -e .
```

Then use either command:

```bash
swf --version
swiftfilez --version
```

A source checkout can also run `python main.py --help`.

## Diagnostics and configuration

```bash
swf doctor
swf doctor --json
swf config
```

| Variable | Purpose | Default |
| --- | --- | --- |
| `SWIFTFILEZ_HASH_ALGORITHM` | Integrity algorithm | `sha256` |
| `SWIFTFILEZ_WORKERS` | Hash/scan worker count (1-32) | `4` |
| `SWIFTFILEZ_QUARANTINE_DIR` | Default duplicate quarantine path | `.swiftfilez-quarantine` |

## CI usage

Gate a release on artifact integrity:

```yaml
- name: Verify release artifacts
  run: swf manifest verify release-manifest.json --root dist --strict
```

Gate automation input quality:

```yaml
- name: Validate deployment inventory
  run: swf csv validate inventory.csv --required service --required environment --required owner
```

## Docker

```bash
docker build -t swiftfilez .
docker run --rm -v "$PWD:/workspace" swiftfilez scan /workspace
```

The image runs as a non-root user.

## Development

```bash
make install
make test
make smoke
make build
make docker-build
```

Local validation for this upgrade: **18 tests passing**, plus CLI smoke tests for version, diagnostics, manifest verification, CSV reporting, and duplicate detection.

## Safety model

- CSV transforms always write to an explicit output path.
- Duplicate cleanup defaults to dry-run.
- Applied duplicate cleanup moves extra copies to quarantine; it does not delete them.
- Manifest verification never modifies artifacts.
- Copies replace the destination atomically after a successful temporary copy.
- Generated JSON/CSV files use same-filesystem atomic replacement where practical.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Operation completed / policy passed |
| `1` | Operational error |
| `2` | Policy or integrity check failed |

See [docs/STRUCTURE.md](docs/STRUCTURE.md) for the code layout.
