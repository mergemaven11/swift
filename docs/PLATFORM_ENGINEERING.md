# Platform Engineering Design Notes

SwiftFilez is intentionally structured like a small internal platform tool rather than a one-off script.

## Design goals

1. **Human and machine interfaces share the same domain logic.** Rich tables are presentation only; `--json` emits stable structured data for scripts and CI.
2. **Read operations are cheap to trust.** Inspection, hashing, scans, and manifest verification never mutate source artifacts.
3. **Mutations are recoverable.** CSV transforms write new files, and duplicate cleanup quarantines extra copies instead of deleting them.
4. **Integrity is explicit.** Manifests record a versioned schema, hash algorithm, relative path, size, modified time, MIME type, and digest.
5. **Policy failure differs from runtime failure.** A drifted manifest or invalid CSV exits `2`; an unreadable file or malformed manifest exits `1`.
6. **Concurrency is bounded.** Directory hashing uses a configurable worker pool capped at 32 workers.
7. **Configuration is deployment-friendly.** Runtime tuning comes from environment variables instead of source edits.

## Architecture

```text
                  +----------------+
                  | Typer CLI      |
                  | Rich / JSON UI |
                  +-------+--------+
                          |
         +----------------+----------------+
         |                |                |
 +-------v------+ +-------v------+ +-------v------+
 | Core artifact| | CSV ops      | | DOCX/PDF ops|
 | scan/hash    | | validate     | | inspect      |
 | manifest     | | dedupe/report| | extract/copy |
 +-------+------+ +-------+------+ +-------+------+
         |                |                |
         +----------------+----------------+
                          |
                  +-------v--------+
                  | Local filesystem|
                  +-----------------+
```

## Integrity workflow

`swf manifest build` recursively inventories a directory and hashes files concurrently. The manifest uses paths relative to the selected root, making it relocatable when `--root` is provided during verification.

`swf manifest verify` checks expected files and hashes. `--strict` additionally rejects unexpected files. The manifest file itself is ignored when it lives inside the verified root so a self-contained manifest can be used safely.

This maps naturally to artifact promotion flows:

```text
build -> create manifest -> publish artifacts -> download -> verify manifest -> deploy
```

## Duplicate detection

Duplicate detection first groups by byte size, then hashes only same-size candidates. That reduces work for heterogeneous directories.

The first path in each identical group is kept. Additional copies are reported. `--apply` moves them to a quarantine directory with collision-resistant names.

## CSV policy gates

`swf csv validate` is designed for configuration/inventory files that feed automation. Required columns are schema-level rules; blank required values are row-level rules. Either condition returns exit code `2`.

`swf csv summarize` generalizes the original debit/credit report concept into a reusable group-and-sum operation.

## Container model

The image runs as a non-root user and treats `/workspace` as mounted input/output. No service port is exposed because SwiftFilez is a batch CLI, not a network daemon.

## CI pipeline

The GitHub Actions workflow contains three stages:

1. **Test matrix** — Python 3.10 through 3.13, compile check, unit tests, and CLI smoke check.
2. **Package** — builds wheel and source distribution after tests pass.
3. **Container** — builds the runtime image and runs `swf doctor` inside it.

The workflow uses read-only repository permissions and cancels superseded runs on the same ref.

## Failure model

Operational errors use exit code `1`; policy failures use exit code `2`. This lets CI differentiate "the tool crashed" from "the tool worked and found a violation."

## Extension points

Future iterations could add S3/GCS adapters, SBOM/provenance ingestion, signed manifests, OPA/Rego policy evaluation, OpenTelemetry, and plugin discovery for more formats.
