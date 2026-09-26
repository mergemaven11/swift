# Signed desktop releases

SwiftFilez publishes platform-specific bundles from dedicated release workflows.

## Windows

The published Windows installer is Authenticode-signed on a dedicated
self-hosted Windows x64 runner labeled `swiftfilez`. The signing certificate
stays in `Cert:\\CurrentUser\\My`; only its thumbprint is stored in the
repository secret `SWIFTFILEZ_SIGN_CERT_SHA1`.

Required local tools:

- Python 3.12+
- Git + GitHub CLI
- Windows SDK Signing Tools (`signtool.exe`)
- Inno Setup 6
- a trusted Authenticode code-signing certificate with private key

The runner service must execute as the Windows user that owns that certificate.

## macOS

The macOS workflow requires an Apple Developer ID Application certificate.
Create these repository secrets:

- `APPLE_CERT_P12_B64` — base64-encoded P12
- `APPLE_CERT_PASSWORD`
- `APPLE_KEYCHAIN_PASSWORD`
- `APPLE_SIGN_IDENTITY` — for example `Developer ID Application: ...`

The workflow imports the certificate into an ephemeral keychain, signs both
binaries with hardened runtime + timestamping, verifies the signatures, and
packages them as `SwiftFilez-macOS.tar.gz`.

Notarization can be added later if a Developer ID team/app-specific credential
is available; code signing itself is already enforced by this workflow.

## Linux

The Linux package is built and tested on Ubuntu and receives a GitHub
cryptographic build-provenance attestation using OIDC. A SHA-256 checksum is
published alongside `SwiftFilez-Linux-x86_64.tar.gz`.

## Rolling downloads

Run each workflow manually from GitHub Actions to refresh:

- `windows-latest`
- `macos-latest`
- `linux-latest`

Version tags such as `v0.4.1` attach the platform bundle to the corresponding
versioned release.

Never commit signing certificates, private keys, PFX passwords, Apple account
credentials, hardware-token PINs, or recovery codes.
