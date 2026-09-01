import json

import pytest

from swift_files.core import (
    SwiftFilezError,
    build_manifest,
    find_duplicates,
    hash_file,
    inspect_file,
    quarantine_duplicates,
    verify_manifest,
    write_manifest,
)


def test_hash_and_inspect(tmp_path):
    file_path = tmp_path / "artifact.txt"
    file_path.write_text("platform", encoding="utf-8")
    digest = hash_file(file_path)
    record = inspect_file(file_path)
    assert len(digest) == 64
    assert record.hash == digest
    assert record.size == 8


def test_manifest_round_trip_and_drift(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.txt").write_text("one", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(root, manifest)
    assert verify_manifest(manifest, root)["ok"] is True
    (root / "a.txt").write_text("two", encoding="utf-8")
    drift = verify_manifest(manifest, root)
    assert drift["ok"] is False
    assert drift["changed"][0]["path"] == "a.txt"


def test_manifest_detects_missing_and_strict_unexpected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.txt").write_text("one", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(root, manifest)
    (root / "a.txt").unlink()
    (root / "b.txt").write_text("new", encoding="utf-8")
    result = verify_manifest(manifest, root, strict=True)
    assert result["missing"] == ["a.txt"]
    assert result["unexpected"] == ["b.txt"]


def test_find_duplicates_and_dry_run(tmp_path):
    (tmp_path / "a.txt").write_text("same", encoding="utf-8")
    (tmp_path / "b.txt").write_text("same", encoding="utf-8")
    (tmp_path / "c.txt").write_text("different", encoding="utf-8")
    groups = find_duplicates(tmp_path)
    assert len(groups) == 1
    result = quarantine_duplicates(groups, tmp_path / "q", apply=False)
    assert len(result["planned"]) == 1
    assert not (tmp_path / "q").exists()


def test_quarantine_apply(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("same", encoding="utf-8")
    b.write_text("same", encoding="utf-8")
    groups = find_duplicates(tmp_path)
    result = quarantine_duplicates(groups, tmp_path / "q", apply=True)
    assert len(result["moved"]) == 1
    assert sum(p.exists() for p in (a, b)) == 1
    assert len(list((tmp_path / "q").iterdir())) == 1


def test_manifest_schema(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"abc")
    manifest = build_manifest(tmp_path)
    assert manifest["schema_version"] == 1
    assert manifest["algorithm"] == "sha256"
    assert manifest["files"][0]["path"] == "a.bin"


def test_manifest_rejects_paths_outside_verification_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "algorithm": "sha256",
                "files": [{"path": "../outside.txt", "hash": hash_file(outside)}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SwiftFilezError, match="escapes verification root"):
        verify_manifest(manifest, root)
