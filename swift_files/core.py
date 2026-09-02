"""Core file and artifact operations."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import tempfile
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import load_settings

CHUNK_SIZE = 1024 * 1024


class SwiftFilezError(RuntimeError):
    """Domain error raised for invalid or unsafe operations."""


@dataclass(frozen=True)
class FileRecord:
    """Represent FileRecord."""

    path: str
    size: int
    modified: str
    mime_type: str | None
    hash: str
    algorithm: str

    def to_dict(self) -> dict:
        """Handle to dict.

        Returns:
            Function result.
        """
        return asdict(self)


def hash_file(path: str | Path, algorithm: str | None = None) -> str:
    """Handle hash file.

    Args:
        path: Function argument.
        algorithm: Function argument.

    Returns:
        Function result.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise SwiftFilezError(f"File not found: {file_path}")
    algo = (algorithm or load_settings().hash_algorithm).lower()
    try:
        digest = hashlib.new(algo)
    except ValueError as exc:
        raise SwiftFilezError(f"Unsupported hash algorithm: {algo}") from exc
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_file(path: str | Path, algorithm: str | None = None, base: Path | None = None) -> FileRecord:
    """Handle inspect file.

    Args:
        path: Function argument.
        algorithm: Function argument.
        base: Function argument.

    Returns:
        Function result.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise SwiftFilezError(f"File not found: {file_path}")
    stat = file_path.stat()
    algo = (algorithm or load_settings().hash_algorithm).lower()
    display = file_path
    if base is not None:
        with suppress(ValueError):
            display = file_path.relative_to(base)
    return FileRecord(
        path=display.as_posix(),
        size=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        mime_type=mimetypes.guess_type(file_path.name)[0],
        hash=hash_file(file_path, algo),
        algorithm=algo,
    )


def iter_files(root: str | Path, include_hidden: bool = False) -> list[Path]:
    """Handle iter files.

    Args:
        root: Function argument.
        include_hidden: Function argument.

    Returns:
        Function result.
    """
    root_path = Path(root)
    if root_path.is_file():
        return [root_path]
    if not root_path.is_dir():
        raise SwiftFilezError(f"Path not found: {root_path}")
    files: list[Path] = []
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if not include_hidden and any(part.startswith(".") for part in path.relative_to(root_path).parts):
            continue
        files.append(path)
    return sorted(files)


def scan_files(
    root: str | Path, *, algorithm: str | None = None, workers: int | None = None, include_hidden: bool = False
) -> list[FileRecord]:
    """Handle scan files.

    Args:
        root: Function argument.
        algorithm: Function argument.
        workers: Function argument.
        include_hidden: Function argument.

    Returns:
        Function result.
    """
    root_path = Path(root)
    base = root_path if root_path.is_dir() else root_path.parent
    files = iter_files(root_path, include_hidden=include_hidden)
    max_workers = workers or load_settings().workers
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(lambda p: inspect_file(p, algorithm, base), files))


def atomic_write_text(path: str | Path, text: str) -> Path:
    """Handle atomic write text.

    Args:
        path: Function argument.
        text: Function argument.

    Returns:
        Function result.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    except Exception:
        with suppress(OSError):
            os.unlink(temp_name)
        raise
    return target


def atomic_write_json(path: str | Path, payload: object) -> Path:
    """Handle atomic write json.

    Args:
        path: Function argument.
        payload: Function argument.

    Returns:
        Function result.
    """
    return atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_manifest(root: str | Path, algorithm: str | None = None, workers: int | None = None) -> dict:
    """Handle build manifest.

    Args:
        root: Function argument.
        algorithm: Function argument.
        workers: Function argument.

    Returns:
        Function result.
    """
    root_path = Path(root).resolve()
    records = scan_files(root_path, algorithm=algorithm, workers=workers)
    algo = (algorithm or load_settings().hash_algorithm).lower()
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": root_path.as_posix(),
        "algorithm": algo,
        "files": [record.to_dict() for record in records],
    }


def write_manifest(
    root: str | Path, output: str | Path, algorithm: str | None = None, workers: int | None = None
) -> Path:
    """Handle write manifest.

    Args:
        root: Function argument.
        output: Function argument.
        algorithm: Function argument.
        workers: Function argument.

    Returns:
        Function result.
    """
    return atomic_write_json(output, build_manifest(root, algorithm=algorithm, workers=workers))


def load_manifest(path: str | Path) -> dict:
    """Handle load manifest.

    Args:
        path: Function argument.

    Returns:
        Function result.
    """
    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SwiftFilezError(f"Could not read manifest: {manifest_path}") from exc
    if payload.get("schema_version") != 1 or not isinstance(payload.get("files"), list):
        raise SwiftFilezError("Unsupported or invalid manifest schema")
    return payload


def verify_manifest(manifest_path: str | Path, root: str | Path | None = None, strict: bool = False) -> dict:
    """Handle verify manifest.

    Args:
        manifest_path: Function argument.
        root: Function argument.
        strict: Function argument.

    Returns:
        Function result.
    """
    manifest = load_manifest(manifest_path)
    root_path = Path(root or manifest.get("root") or ".").resolve()
    algorithm = manifest.get("algorithm", "sha256")
    expected = {item["path"]: item for item in manifest["files"]}
    missing: list[str] = []
    changed: list[dict] = []
    for rel_path, record in expected.items():
        if not isinstance(rel_path, str) or not rel_path:
            raise SwiftFilezError("Manifest contains an invalid file path")
        target = (root_path / rel_path).resolve()
        try:
            target.relative_to(root_path)
        except ValueError as exc:
            raise SwiftFilezError(f"Manifest path escapes verification root: {rel_path}") from exc
        if not target.is_file():
            missing.append(rel_path)
            continue
        current_hash = hash_file(target, algorithm)
        if current_hash != record.get("hash"):
            changed.append({"path": rel_path, "expected": record.get("hash"), "actual": current_hash})
    unexpected: list[str] = []
    if strict:
        current = {p.relative_to(root_path).as_posix() for p in iter_files(root_path)}
        try:
            manifest_rel = Path(manifest_path).resolve().relative_to(root_path).as_posix()
            current.discard(manifest_rel)
        except ValueError:
            pass
        unexpected = sorted(current - set(expected))
    ok = not missing and not changed and not unexpected
    return {
        "ok": ok,
        "root": root_path.as_posix(),
        "checked": len(expected),
        "missing": missing,
        "changed": changed,
        "unexpected": unexpected,
    }


def find_duplicates(root: str | Path, algorithm: str | None = None, workers: int | None = None) -> list[list[Path]]:
    """Handle find duplicates.

    Args:
        root: Function argument.
        algorithm: Function argument.
        workers: Function argument.

    Returns:
        Function result.
    """
    files = iter_files(root)
    by_size: dict[int, list[Path]] = {}
    for file_path in files:
        by_size.setdefault(file_path.stat().st_size, []).append(file_path)
    candidates = [path for group in by_size.values() if len(group) > 1 for path in group]
    if not candidates:
        return []
    algo = algorithm or load_settings().hash_algorithm
    max_workers = workers or load_settings().workers
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        hashed = list(pool.map(lambda p: (p, hash_file(p, algo)), candidates))
    by_hash: dict[str, list[Path]] = {}
    for path, digest in hashed:
        by_hash.setdefault(digest, []).append(path)
    return [sorted(group) for group in by_hash.values() if len(group) > 1]


def quarantine_duplicates(groups: Iterable[Iterable[Path]], quarantine_dir: str | Path, *, apply: bool = False) -> dict:
    """Handle quarantine duplicates.

    Args:
        groups: Function argument.
        quarantine_dir: Function argument.
        apply: Function argument.

    Returns:
        Function result.
    """
    quarantine = Path(quarantine_dir)
    planned: list[dict] = []
    moved: list[dict] = []
    for group in groups:
        paths = list(group)
        for duplicate in paths[1:]:
            destination = quarantine / f"{duplicate.stem}-{uuid4().hex[:8]}{duplicate.suffix}"
            action = {"source": duplicate.as_posix(), "destination": destination.as_posix()}
            planned.append(action)
            if apply:
                quarantine.mkdir(parents=True, exist_ok=True)
                shutil.move(str(duplicate), str(destination))
                moved.append(action)
    return {"apply": apply, "planned": planned, "moved": moved}


def safe_copy(source: str | Path, destination: str | Path) -> Path:
    """Handle safe copy.

    Args:
        source: Function argument.
        destination: Function argument.

    Returns:
        Function result.
    """
    src = Path(source)
    dst = Path(destination)
    if not src.is_file():
        raise SwiftFilezError(f"File not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    temp = dst.with_name(f".{dst.name}.{uuid4().hex}.tmp")
    shutil.copy2(src, temp)
    os.replace(temp, dst)
    return dst
