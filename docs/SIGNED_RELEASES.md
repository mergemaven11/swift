# Signed desktop releases

SwiftFilez publishes platform-specific bundles from dedicated release workflows.

## Windows

The published Windows installer is designed to be Authenticode-signed on a dedicated
self-hosted Windows x64 runner labeled `swiftfilez`. The signing certificate
stays in `Cert:\\CurrentUser\\My`; only its thumbprint is stored in the
repository secret `SWIFTFILEZ_SIGN_CERT_SHA1`.

The Windows installer presents the SwiftFilez EULA and privacy notice, installs
both the desktop/TUI launcher and `swf.exe`, and can add the install directory
to the current user's PATH.

Required signing tools:

- Python 3.12+
- Git + GitHub CLI
- Windows SDK Signing Tools (`signtool.exe`)
- Inno Setup 6
- a trusted Authenticode code-signing certificate with private key

## Linux

The Linux release is built on the self-hosted Linux x64 runner labeled
`swiftfilez`. It contains standalone PyInstaller binaries, so end users do not
need Python or a virtual environment.

The archive contains:

- `swf` — CLI
- `SwiftFilez` — terminal UI launcher
- `install.sh` — per-user installer
- `uninstall.sh`
- `EULA.txt`
- `PRIVACY.txt`
- `README.md` and `LICENSE`

The installer places application files under
`~/.local/share/swiftfilez`, creates command links in `~/.local/bin`, and
adds `~/.local/bin` to the appropriate shell profile when needed. No sudo is
required for the default install.

Typical installation:

```bash
tar -xzf SwiftFilez-Linux-x86_64.tar.gz
./install.sh
```

After opening a new terminal:

```bash
swf --version
swf ui .
```

A SHA-256 checksum and GitHub build-provenance attestation are published with
the archive.

## macOS

The macOS workflow requires an Apple Developer ID Application certificate for
a polished signed distribution. The intended end-user experience is a signed
app/binary bundle with `swf` available from the shell and the same EULA/privacy
materials included.

Required secrets:

- `APPLE_CERT_P12_B64`
- `APPLE_CERT_PASSWORD`
- `APPLE_KEYCHAIN_PASSWORD`
- `APPLE_SIGN_IDENTITY`

Notarization should be enabled before treating a macOS build as a normal
Gatekeeper-friendly public download.

## Rolling downloads

Run the platform release workflow manually to refresh:

- `windows-latest`
- `macos-latest`
- `linux-latest`

Version tags such as `v0.5.0` attach platform bundles to the corresponding
versioned release.

Never commit signing certificates, private keys, PFX passwords, Apple account
credentials, hardware-token PINs, or recovery codes.
