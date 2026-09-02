"""Registry-driven artifact type detection and safe metadata inspection."""

from __future__ import annotations

import gzip
import json
import tarfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree

from .core import SwiftFilezError

MAX_CONTAINER_ENTRIES = 1000
MAX_TEXT_PROBE = 1024 * 1024


@dataclass(frozen=True)
class FormatInfo:
    format: str
    family: str
    extension: str
    container: bool
    metadata: dict

    def to_dict(self) -> dict:
        return asdict(self)


_FILENAME_FORMATS = {
    "dockerfile": ("dockerfile", "infrastructure"),
    "compose.yaml": ("docker-compose", "infrastructure"),
    "compose.yml": ("docker-compose", "infrastructure"),
    "docker-compose.yaml": ("docker-compose", "infrastructure"),
    "docker-compose.yml": ("docker-compose", "infrastructure"),
    "package.json": ("npm-manifest", "dependency-manifest"),
    "package-lock.json": ("npm-lockfile", "dependency-manifest"),
    "yarn.lock": ("yarn-lockfile", "dependency-manifest"),
    "pnpm-lock.yaml": ("pnpm-lockfile", "dependency-manifest"),
    "requirements.txt": ("python-requirements", "dependency-manifest"),
    "pyproject.toml": ("python-project", "dependency-manifest"),
    "poetry.lock": ("poetry-lockfile", "dependency-manifest"),
    "pipfile.lock": ("pipenv-lockfile", "dependency-manifest"),
    "go.mod": ("go-module", "dependency-manifest"),
    "go.sum": ("go-checksums", "dependency-manifest"),
    "cargo.toml": ("cargo-manifest", "dependency-manifest"),
    "cargo.lock": ("cargo-lockfile", "dependency-manifest"),
    "gemfile.lock": ("ruby-bundler-lockfile", "dependency-manifest"),
    "composer.lock": ("composer-lockfile", "dependency-manifest"),
    "pom.xml": ("maven-pom", "dependency-manifest"),
    "jenkinsfile": ("jenkins-pipeline", "ci-config"),
    ".gitlab-ci.yml": ("gitlab-ci", "ci-config"),
    ".gitlab-ci.yaml": ("gitlab-ci", "ci-config"),
}

_EXTENSION_FORMATS = {
    ".csv": ("csv", "data"),
    ".tsv": ("tsv", "data"),
    ".json": ("json", "structured-data"),
    ".yaml": ("yaml", "structured-data"),
    ".yml": ("yaml", "structured-data"),
    ".toml": ("toml", "structured-data"),
    ".xml": ("xml", "structured-data"),
    ".ini": ("ini", "configuration"),
    ".env": ("dotenv", "configuration"),
    ".md": ("markdown", "document"),
    ".log": ("log", "text"),
    ".txt": ("text", "text"),
    ".tf": ("terraform", "infrastructure"),
    ".tfvars": ("terraform-vars", "infrastructure"),
    ".jar": ("jar", "java-package"),
    ".war": ("war", "java-package"),
    ".whl": ("python-wheel", "python-package"),
    ".egg": ("python-egg", "python-package"),
    ".nupkg": ("nuget-package", "dotnet-package"),
    ".apk": ("android-apk", "mobile-package"),
    ".ipa": ("ios-ipa", "mobile-package"),
    ".deb": ("debian-package", "os-package"),
    ".rpm": ("rpm-package", "os-package"),
    ".wasm": ("webassembly", "binary"),
    ".exe": ("pe-executable", "binary"),
    ".dll": ("pe-library", "binary"),
    ".so": ("elf-library", "binary"),
    ".dylib": ("mach-o-library", "binary"),
    ".pem": ("pem", "certificate-or-key"),
    ".crt": ("certificate", "certificate-or-key"),
    ".cer": ("certificate", "certificate-or-key"),
    ".der": ("der", "certificate-or-key"),
}


def _read_probe(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(MAX_TEXT_PROBE)


def _classify_json(payload: object, default: tuple[str, str]) -> tuple[str, str, dict]:
    metadata: dict = {}
    if isinstance(payload, dict):
        if "bomFormat" in payload and str(payload.get("bomFormat", "")).lower() == "cyclonedx":
            metadata["spec_version"] = payload.get("specVersion")
            return "cyclonedx-sbom", "sbom", metadata
        if "spdxVersion" in payload:
            metadata["spdx_version"] = payload.get("spdxVersion")
            return "spdx-sbom", "sbom", metadata
        if payload.get("predicateType") or payload.get("_type") == "https://in-toto.io/Statement/v0.1":
            metadata["predicate_type"] = payload.get("predicateType")
            return "in-toto-attestation", "provenance", metadata
        if "runs" in payload and "version" in payload:
            return "sarif", "security-report", metadata
        if "schemaVersion" in payload and "manifests" in payload:
            return "oci-index-or-manifest", "container-metadata", metadata
    return default[0], default[1], metadata


def _inspect_zip(path: Path, base_format: str, family: str) -> FormatInfo:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            limited = names[:MAX_CONTAINER_ENTRIES]
            detected = base_format
            detected_family = family
            if "META-INF/MANIFEST.MF" in names and path.suffix.lower() == ".jar":
                detected = "jar"
            elif path.suffix.lower() == ".whl" or any(name.endswith(".dist-info/WHEEL") for name in names):
                detected, detected_family = "python-wheel", "python-package"
            elif path.suffix.lower() == ".nupkg" or any(name.endswith(".nuspec") for name in names):
                detected, detected_family = "nuget-package", "dotnet-package"
            elif "AndroidManifest.xml" in names:
                detected, detected_family = "android-apk", "mobile-package"
            elif any(name.startswith("Payload/") and name.endswith(".app/Info.plist") for name in names):
                detected, detected_family = "ios-ipa", "mobile-package"
            metadata = {
                "entries": len(names),
                "sample_entries": limited[:25],
                "truncated": len(names) > MAX_CONTAINER_ENTRIES,
            }
            return FormatInfo(detected, detected_family, path.suffix.lower(), True, metadata)
    except (OSError, zipfile.BadZipFile) as exc:
        raise SwiftFilezError(f"Could not inspect ZIP-compatible artifact: {path}") from exc


def _inspect_tar(path: Path) -> FormatInfo:
    try:
        with tarfile.open(path, mode="r:*") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            fmt, family = "tar-archive", "archive"
            if "manifest.json" in names and any(name.endswith("/layer.tar") or name.endswith("layer.tar") for name in names):
                fmt, family = "docker-image-archive", "container-image"
            elif "oci-layout" in names and "index.json" in names:
                fmt, family = "oci-image-layout", "container-image"
            return FormatInfo(
                fmt,
                family,
                "".join(path.suffixes[-2:]) if len(path.suffixes) > 1 else path.suffix.lower(),
                True,
                {"entries": len(names), "sample_entries": names[:25], "truncated": len(names) > MAX_CONTAINER_ENTRIES},
            )
    except (OSError, tarfile.TarError) as exc:
        raise SwiftFilezError(f"Could not inspect TAR-compatible artifact: {path}") from exc


def inspect_format(path: str | Path) -> FormatInfo:
    file_path = Path(path)
    if not file_path.is_file():
        raise SwiftFilezError(f"File not found: {file_path}")

    lower_name = file_path.name.lower()
    suffix = file_path.suffix.lower()
    suffixes = [part.lower() for part in file_path.suffixes]
    named = _FILENAME_FORMATS.get(lower_name)
    base = named or _EXTENSION_FORMATS.get(suffix) or ("unknown", "unknown")

    if zipfile.is_zipfile(file_path):
        return _inspect_zip(file_path, base[0] if base[0] != "unknown" else "zip-archive", base[1] if base[1] != "unknown" else "archive")
    if tarfile.is_tarfile(file_path):
        return _inspect_tar(file_path)

    probe = _read_probe(file_path)
    if probe.startswith(b"\x7fELF"):
        return FormatInfo("elf", "binary", suffix, False, {})
    if probe.startswith(b"MZ"):
        return FormatInfo("pe", "binary", suffix, False, {})
    if probe.startswith(b"\x00asm"):
        return FormatInfo("webassembly", "binary", suffix, False, {})
    if probe.startswith((b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe")):
        return FormatInfo("mach-o", "binary", suffix, False, {})
    if probe.startswith(b"\x1f\x8b") and not ({".tar", ".tgz"} & set(suffixes)):
        metadata = {}
        try:
            with gzip.open(file_path, "rb") as handle:
                metadata["uncompressed_probe_bytes"] = len(handle.read(4096))
        except OSError:
            pass
        return FormatInfo("gzip", "archive", suffix, True, metadata)

    if suffix == ".json" or lower_name.endswith(".spdx.json") or lower_name.endswith(".cdx.json"):
        try:
            payload = json.loads(probe.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return FormatInfo(base[0], base[1], suffix, False, {"valid_json": False})
        fmt, family, metadata = _classify_json(payload, base)
        metadata["valid_json"] = True
        return FormatInfo(fmt, family, suffix, False, metadata)

    if suffix == ".xml" or lower_name.endswith(".spdx.xml") or lower_name.endswith(".cdx.xml"):
        try:
            root = ElementTree.fromstring(probe)
            tag = root.tag.lower()
            fmt, family = base
            if "cyclonedx" in tag or tag.endswith("bom"):
                fmt, family = "cyclonedx-sbom", "sbom"
            return FormatInfo(fmt, family, suffix, False, {"root_tag": root.tag, "valid_xml": True})
        except ElementTree.ParseError:
            return FormatInfo(base[0], base[1], suffix, False, {"valid_xml": False})

    return FormatInfo(base[0], base[1], suffix, False, {})


def supported_formats() -> list[str]:
    formats = {value[0] for value in _FILENAME_FORMATS.values()}
    formats.update(value[0] for value in _EXTENSION_FORMATS.values())
    formats.update(
        {
            "zip-archive",
            "tar-archive",
            "gzip",
            "docker-image-archive",
            "oci-image-layout",
            "cyclonedx-sbom",
            "spdx-sbom",
            "in-toto-attestation",
            "sarif",
            "elf",
            "pe",
            "mach-o",
            "webassembly",
        }
    )
    return sorted(formats)
