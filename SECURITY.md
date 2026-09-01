# Security policy

## Supported versions

Security fixes are applied to the latest release on the `main` branch.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting feature instead of opening
a public issue. Include the affected command, a minimal reproduction, the
security impact, and any suggested mitigation.

Do not include sensitive production files, credentials, customer data, or
other private artifacts in a report.

## Security model

SwiftFilez operates on local files with the permissions of the current user.
Mutation commands are designed to be explicit and recoverable: duplicate
cleanup is a dry run unless `--apply` is supplied, and duplicate files are
moved to quarantine instead of deleted.

Integrity manifests are treated as untrusted input. Manifest paths must remain
inside the selected verification root.
