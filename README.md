<div align="center">

<img src="./assets/file.gif" alt="SwiftFilez animated file operations demo" width="260" />

# SwiftFilez

**Safe file and artifact operations for humans, scripts, and CI pipelines.**

`swf` gives developers and platform teams one CLI for artifact inspection, integrity verification, duplicate discovery, CSV data operations, DOCX/PDF extraction, and automation-friendly diagnostics.

![Python](https://img.shields.io/badge/Python-3.10%20%E2%80%93%203.13-3776AB?logo=python&logoColor=white)
![CLI](https://img.shields.io/badge/CLI-Typer%20%2B%20Rich-7C3AED)
![Docker](https://img.shields.io/badge/Docker-non--root-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## Why SwiftFilez exists

Build and platform workflows constantly move files between developers, CI jobs, release directories, deployment systems, and archives. Those workflows need more than `cp` and a few one-off scripts: they need **integrity checks, deterministic output, safe mutation behavior, machine-readable results, and useful failure codes**.

SwiftFilez started as a small file-manipulation experiment. It is now a production-minded artifact operations CLI designed around those operational concerns.

### Platform Engineering signals

| Capability | Why it matters |
| --- | --- |
| **Artifact integrity** | SHA-256 by default, versioned manifests, and drift verification |
| **Automation contracts** | `--json` output for scripts, CI jobs, and other tooling |
| **Policy gates** | Validation/integrity failures return exit code `2` |
| **Safe mutations** | Duplicate cleanup is dry-run by default and quarantines instead of deleting |
| **Concurrency** | Directory scans and duplicate hashing use a bounded worker pool |
| **Runtime configuration** | Environment variables instead of workstation-specific assumptions |
| **Packaging** | Installable `swf` and `swiftfilez` console commands |
| **Containers** | Non-root Docker image with `/workspace` volume semantics |
| **CI/CD** | Python 3.10–3.13 test matrix, package build, and container smoke test |
| **Diagnostics** | `swf doctor` provides a health/self-check for local and CI environments |

See [`docs/PLATFORM_ENGINEERING.md`](docs/PLATFORM_ENGINEERING.md) for the architecture, reliability model, and design tradeoffs.

---

## Quick start

### Install from a checkout

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

Install SwiftFilez:

```bash
python -m pip install -e .
```

Verify the installation:

```bash
swf --version
swf doctor
```

Launch the interactive artifact console:

```bash
swf ui
```

The full-screen terminal dashboard provides directory scanning, artifact
metrics, inventory results, metadata, MIME types, and SHA-256 digests while
keeping every operation local to your machine.

A source checkout can also run:

```bash
python main.py --help
```

---

## Command map

```text
swf
├── ui                      launch the interactive artifact dashboard
├── inspect                 inspect a file and calculate metadata/hash
├── hash                    calculate a cryptographic digest
├── scan                    inventory a directory concurrently
├── duplicates              detect identical artifacts / quarantine extras
├── doctor                  environment and dependency diagnostics
├── config                  show effective runtime configuration
├── manifest
│   ├── build               generate a versioned integrity manifest
│   └── verify              detect missing, changed, or unexpected files
├── csv
│   ├── inspect             schema + row overview
│   ├── duplicates          find duplicate rows
│   ├── dedupe              write a cleaned CSV
│   ├── sort                sort by a selected column
│   ├── validate            enforce required fields
│   └── summarize           grouped numeric reporting
├── docx
│   ├── inspect
│   ├── extract
│   └── copy
└── pdf
    ├── inspect
    ├── extract
    └── copy
```

---

## Artifact inspection and hashing

Inspect a release artifact:

```bash
swf inspect ./release.tar.gz
```

Calculate a different digest:

```bash
swf hash ./release.tar.gz --algorithm sha512
```

Inventory a build directory:

```bash
swf scan ./dist
swf scan ./dist --json
```

The JSON form is useful when another script, CI job, or platform service needs to consume the result.

---

## Duplicate artifact detection

Discover byte-identical files:

```bash
swf duplicates ./artifacts
```

By default this is **read-only**. To move redundant copies into quarantine:

```bash
swf duplicates ./artifacts \
  --apply \
  --quarantine-dir ./quarantine
```

SwiftFilez does **not** delete detected duplicates. Applied cleanup moves extra copies into a recoverable quarantine directory.

---

## Integrity manifests and drift detection

Build a manifest for release artifacts:

```bash
swf manifest build ./dist --output release-manifest.json
```

Verify it later:

```bash
swf manifest verify release-manifest.json --root ./dist --strict
```

Machine-readable verification:

```bash
swf manifest verify release-manifest.json \
  --root ./dist \
  --strict \
  --json
```

A clean verification exits `0`. Integrity drift exits `2`, so this can serve directly as a release/deployment policy gate.

### CI example

```yaml
- name: Verify release artifacts
  run: swf manifest verify release-manifest.json --root dist --strict
```

---

## CSV operations

Inspect a dataset:

```bash
swf csv inspect customers.csv
```

Find duplicates by a business key:

```bash
swf csv duplicates customers.csv --key customer_id
```

Write a deduplicated output file:

```bash
swf csv dedupe customers.csv \
  --key customer_id \
  --output customers-clean.csv
```

Sort a CSV:

```bash
swf csv sort customers.csv \
  --column customer \
  --output customers-sorted.csv
```

Validate automation inputs:

```bash
swf csv validate inventory.csv \
  --required service \
  --required environment \
  --required owner
```

### Grouped reports

The original SwiftFilez concept included a customer credit/debit report. That functionality is now implemented generically:

```bash
swf csv summarize ledger.csv \
  --group-by customer \
  --sum credit \
  --sum debit
```

The same command can summarize other numeric datasets without hard-coding a finance-specific schema.

---

## DOCX operations

```bash
swf docx inspect runbook.docx
swf docx extract runbook.docx --output runbook.txt
swf docx copy runbook.docx --output backup/runbook.docx
```

Inspection includes document metadata plus paragraph, table, and word counts. Extraction includes table text.

---

## PDF operations

```bash
swf pdf inspect architecture.pdf
swf pdf extract architecture.pdf --output architecture.txt
swf pdf copy architecture.pdf --output backup/architecture.pdf
```

Encrypted PDFs can be inspected or extracted with `--password`.

> Earlier versions of the README mentioned PDF signing as a TODO. Signing is intentionally not advertised because it is not implemented. The documented command surface matches tested functionality.

---

## Diagnostics and configuration

```bash
swf doctor
swf doctor --json
swf config
```

| Environment variable | Purpose | Default |
| --- | --- | --- |
| `SWIFTFILEZ_HASH_ALGORITHM` | Integrity algorithm | `sha256` |
| `SWIFTFILEZ_WORKERS` | Hash/scan worker count (`1`–`32`) | `4` |
| `SWIFTFILEZ_QUARANTINE_DIR` | Default duplicate quarantine path | `.swiftfilez-quarantine` |

Environment-driven configuration makes the CLI easy to use in laptops, build agents, containers, and ephemeral CI environments without rewriting configuration files.

---

## Docker

Build the image:

```bash
docker build -t swiftfilez .
```

Operate on the current directory:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  swiftfilez scan /workspace
```

The container runs as a **non-root user**.

---

## CI/CD

The repository CI validates:

- Python **3.10**
- Python **3.11**
- Python **3.12**
- Python **3.13**
- source compilation
- the full pytest suite
- installed CLI smoke tests
- Python package construction
- Docker image construction
- container smoke tests

The platform upgrade was validated locally with **18 passing tests**, and its first GitHub Actions run completed successfully across the full Python matrix, package build, and Docker container jobs.

---

## Development

```bash
make install
make test
make smoke
make build
make docker-build
```

Useful documentation:

- [`docs/PLATFORM_ENGINEERING.md`](docs/PLATFORM_ENGINEERING.md) — architecture and operational design
- [`docs/STRUCTURE.md`](docs/STRUCTURE.md) — repository layout
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — contribution workflow

---

## Safety model

SwiftFilez deliberately favors recoverability over clever destructive behavior:

- CSV transforms write to an explicit output path.
- Duplicate cleanup defaults to dry-run.
- Applied duplicate cleanup moves extra copies to quarantine instead of deleting them.
- Manifest verification never modifies artifacts.
- File copies replace destinations atomically after a successful temporary copy.
- Generated JSON and CSV outputs use same-filesystem atomic replacement where practical.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Operation completed / policy passed |
| `1` | Operational error |
| `2` | Policy or integrity check failed |

That exit-code contract allows SwiftFilez to work equally well for a person at a terminal or as a component inside CI/CD and platform automation.

---

<div align="center">

**SwiftFilez — inspect it, verify it, move it safely.**

</div>
