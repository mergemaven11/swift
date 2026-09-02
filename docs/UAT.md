# SwiftFilez UAT Plan

Swift enters User Acceptance Testing when the release candidate is feature-complete for the beta acceptance scope, passes CI on every supported Python version, builds as a Python package and container, and exposes the acceptance workflows through the primary `swf` command.

## Beta acceptance scope

UAT validates that a platform/release/DevSecOps user can:

1. Install Swift and run `swf --version` and `swf doctor`.
2. Inspect a normal file with `swf inspect FILE`.
3. Identify software-artifact formats without a network connection.
4. Recursively inspect ZIP/TAR software artifacts with bounded recursion.
5. Discover nested SBOMs and dependency manifests.
6. Normalize CycloneDX components and SPDX packages.
7. Produce stable JSON suitable for CI automation.
8. Gate a release with `swf policy check ARTIFACT --policy POLICY.json`.
9. Receive exit code 0 for acceptance, 2 for policy rejection/drift, and 1 for operational errors.
10. Build and verify integrity manifests.
11. Find duplicate files without deleting them by default.
12. Use CSV, DOCX, and PDF operations already included in SwiftFilez.
13. Run the package and container smoke tests successfully.

## UAT scenarios

### UAT-01 — Local artifact identification

```bash
swf inspect package.json --json
```

Expected: exit 0 and artifact family `dependency-manifest`.

### UAT-02 — Recursive release inspection

```bash
swf inspect release.zip --recursive --json
```

Expected: exit 0, SHA-256 identity, nested artifact tree, roll-up summary, and no network/API requirement.

### UAT-03 — SBOM normalization

Inspect a release containing a CycloneDX or SPDX SBOM.

Expected: normalized component/package records and quality findings.

### UAT-04 — Policy acceptance

```bash
swf policy check release.zip --policy examples/uat-policy.json --json
```

Expected for a compliant release: exit 0 and `ok: true`.

### UAT-05 — Policy rejection

Run the same policy against a release with no SBOM.

Expected: exit 2, `ok: false`, and a `required-family-missing` violation.

### UAT-06 — Integrity drift

Build an integrity manifest, modify a tracked file, then verify the manifest.

Expected: verification reports drift and exits 2.

### UAT-07 — Safe duplicate workflow

Run duplicate detection without `--apply`.

Expected: a dry-run plan only; no files are moved or deleted.

### UAT-08 — Offline operation

Disable network access and repeat UAT-01 through UAT-07.

Expected: all core acceptance scenarios continue to work.

## UAT entry gate

- [ ] Python 3.10 CI passes
- [ ] Python 3.11 CI passes
- [ ] Python 3.12 CI passes
- [ ] Python 3.13 CI passes
- [ ] Ruff lint/format passes
- [ ] Dependency audit passes
- [ ] Package build passes
- [ ] Container build and smoke test pass
- [ ] UAT CLI acceptance tests pass
- [ ] Primary `swf` command exposes artifact inspection and policy gates
- [ ] Help Center/docs describe the acceptance workflows

When every entry item is green, the beta is **UAT-ready**. Sigstore/Cosign, OPA/Rego, cloud adapters, plugin discovery, and OpenTelemetry are post-beta enhancements and are not blockers for this UAT scope.
