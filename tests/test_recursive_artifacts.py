"""Document this first-party Python module."""

import json
import zipfile
from pathlib import Path

from swift_files.artifacts import inspect_artifact


def test_recursive_inspection_finds_nested_sbom(tmp_path: Path):
    """Verify recursive inspection finds nested sbom.

    Args:
        tmp_path: Function argument.
    """
    inner = tmp_path / "bom.cdx.json"
    inner.write_text(
        json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6", "components": []}),
        encoding="utf-8",
    )
    outer = tmp_path / "release.zip"
    with zipfile.ZipFile(outer, "w") as archive:
        archive.write(inner, arcname="metadata/bom.cdx.json")
        archive.writestr("README.txt", "not an artifact finding")

    result = inspect_artifact(outer)

    assert result.format == "zip-archive"
    assert len(result.children) == 1
    assert result.children[0].name == "metadata/bom.cdx.json"
    assert result.children[0].format == "cyclonedx-sbom"
    assert result.children[0].family == "sbom"
    assert len(result.sha256) == 64


def test_recursive_inspection_finds_nested_dependency_manifest(tmp_path: Path):
    """Verify recursive inspection finds nested dependency manifest.

    Args:
        tmp_path: Function argument.
    """
    outer = tmp_path / "source.zip"
    with zipfile.ZipFile(outer, "w") as archive:
        archive.writestr("app/package.json", '{"name":"demo"}')

    result = inspect_artifact(outer)

    assert result.children[0].name == "app/package.json"
    assert result.children[0].format == "npm-manifest"
    assert result.children[0].family == "dependency-manifest"


def test_recursive_inspection_respects_depth(tmp_path: Path):
    """Verify recursive inspection respects depth.

    Args:
        tmp_path: Function argument.
    """
    inner = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner, "w") as archive:
        archive.writestr("package.json", '{"name":"nested"}')
    outer = tmp_path / "outer.zip"
    with zipfile.ZipFile(outer, "w") as archive:
        archive.write(inner, arcname="inner.zip")

    result = inspect_artifact(outer, max_depth=1)

    assert len(result.children) == 1
    assert result.children[0].format == "zip-archive"
    assert result.children[0].children == []


def test_recursive_inspection_respects_child_limit(tmp_path: Path):
    """Verify recursive inspection respects child limit.

    Args:
        tmp_path: Function argument.
    """
    outer = tmp_path / "many.zip"
    with zipfile.ZipFile(outer, "w") as archive:
        for index in range(3):
            archive.writestr(f"pkg{index}/package.json", '{"name":"demo"}')

    result = inspect_artifact(outer, max_children=2)

    assert len(result.children) == 2
    assert "child limit reached (2)" in result.warnings
