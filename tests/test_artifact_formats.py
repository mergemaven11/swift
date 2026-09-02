"""Document this first-party Python module."""

import json
import tarfile
import zipfile
from pathlib import Path

from swift_files.formats import inspect_format, supported_formats


def test_detects_dependency_manifest_by_filename(tmp_path: Path):
    """Verify detects dependency manifest by filename.

    Args:
        tmp_path: Function argument.
    """
    path = tmp_path / "package.json"
    path.write_text('{"name": "demo"}', encoding="utf-8")

    result = inspect_format(path)

    assert result.format == "npm-manifest"
    assert result.family == "dependency-manifest"
    assert result.metadata["valid_json"] is True


def test_detects_cyclonedx_json_sbom(tmp_path: Path):
    """Verify detects cyclonedx json sbom.

    Args:
        tmp_path: Function argument.
    """
    path = tmp_path / "bom.cdx.json"
    path.write_text(json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6", "components": []}), encoding="utf-8")

    result = inspect_format(path)

    assert result.format == "cyclonedx-sbom"
    assert result.family == "sbom"
    assert result.metadata["spec_version"] == "1.6"


def test_detects_spdx_json_sbom(tmp_path: Path):
    """Verify detects spdx json sbom.

    Args:
        tmp_path: Function argument.
    """
    path = tmp_path / "inventory.spdx.json"
    path.write_text(json.dumps({"spdxVersion": "SPDX-2.3", "packages": []}), encoding="utf-8")

    result = inspect_format(path)

    assert result.format == "spdx-sbom"
    assert result.family == "sbom"
    assert result.metadata["spdx_version"] == "SPDX-2.3"


def test_detects_in_toto_attestation(tmp_path: Path):
    """Verify detects in toto attestation.

    Args:
        tmp_path: Function argument.
    """
    path = tmp_path / "provenance.json"
    path.write_text(
        json.dumps({"_type": "https://in-toto.io/Statement/v0.1", "predicateType": "https://slsa.dev/provenance/v1"}),
        encoding="utf-8",
    )

    result = inspect_format(path)

    assert result.format == "in-toto-attestation"
    assert result.family == "provenance"


def test_detects_python_wheel_from_zip_contents(tmp_path: Path):
    """Verify detects python wheel from zip contents.

    Args:
        tmp_path: Function argument.
    """
    path = tmp_path / "demo-1.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("demo-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
        archive.writestr("demo/__init__.py", "")

    result = inspect_format(path)

    assert result.format == "python-wheel"
    assert result.family == "python-package"
    assert result.container is True
    assert result.metadata["entries"] == 2


def test_detects_android_apk_from_zip_contents(tmp_path: Path):
    """Verify detects android apk from zip contents.

    Args:
        tmp_path: Function argument.
    """
    path = tmp_path / "demo.apk"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AndroidManifest.xml", b"manifest")
        archive.writestr("classes.dex", b"dex")

    result = inspect_format(path)

    assert result.format == "android-apk"
    assert result.family == "mobile-package"


def test_detects_oci_image_layout_tar(tmp_path: Path):
    """Verify detects oci image layout tar.

    Args:
        tmp_path: Function argument.
    """
    root = tmp_path / "oci"
    root.mkdir()
    (root / "oci-layout").write_text('{"imageLayoutVersion":"1.0.0"}', encoding="utf-8")
    (root / "index.json").write_text('{"schemaVersion":2,"manifests":[]}', encoding="utf-8")
    path = tmp_path / "image.tar"
    with tarfile.open(path, "w") as archive:
        archive.add(root / "oci-layout", arcname="oci-layout")
        archive.add(root / "index.json", arcname="index.json")

    result = inspect_format(path)

    assert result.format == "oci-image-layout"
    assert result.family == "container-image"
    assert result.container is True


def test_detects_binary_magic_over_extension(tmp_path: Path):
    """Verify detects binary magic over extension.

    Args:
        tmp_path: Function argument.
    """
    path = tmp_path / "mystery.bin"
    path.write_bytes(b"\x7fELF" + b"\x00" * 32)

    result = inspect_format(path)

    assert result.format == "elf"
    assert result.family == "binary"


def test_supported_formats_include_supply_chain_and_packages():
    """Verify supported formats include supply chain and packages."""
    formats = supported_formats()

    assert "cyclonedx-sbom" in formats
    assert "spdx-sbom" in formats
    assert "in-toto-attestation" in formats
    assert "python-wheel" in formats
    assert "docker-image-archive" in formats
    assert "terraform" in formats
