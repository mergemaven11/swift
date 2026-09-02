"""Local-first recursive artifact inspection."""

from __future__ import annotations

import hashlib
import tarfile
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .formats import FormatInfo, inspect_format
from .intelligence import analyze_sbom

DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_CHILDREN = 100
DEFAULT_MAX_MEMBER_BYTES = 64 * 1024 * 1024


@dataclass
class ArtifactNode:
    name: str
    format: str
    family: str
    size: int
    sha256: str
    metadata: dict = field(default_factory=dict)
    components: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    children: list[ArtifactNode] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["summary"] = _summarize(self)
        return payload


def _summarize(node: ArtifactNode) -> dict:
    nodes = 1
    components = len(node.components)
    findings = len(node.findings)
    severities: dict[str, int] = {}
    families: dict[str, int] = {node.family: 1}
    for finding in node.findings:
        severity = str(finding.get("severity", "unknown"))
        severities[severity] = severities.get(severity, 0) + 1
    for child in node.children:
        summary = _summarize(child)
        nodes += summary["artifacts"]
        components += summary["components"]
        findings += summary["findings"]
        for severity, count in summary["findings_by_severity"].items():
            severities[severity] = severities.get(severity, 0) + count
        for family, count in summary["families"].items():
            families[family] = families.get(family, 0) + count
    return {
        "artifacts": nodes,
        "components": components,
        "findings": findings,
        "findings_by_severity": severities,
        "families": families,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _interesting(info: FormatInfo) -> bool:
    return info.container or info.family in {
        "sbom",
        "provenance",
        "security-report",
        "dependency-manifest",
        "container-metadata",
        "os-package",
        "python-package",
        "java-package",
        "dotnet-package",
        "mobile-package",
    }


def _safe_member_name(name: str) -> str:
    return Path(name).name or "artifact"


def _inspect_extracted(
    path: Path,
    display_name: str,
    depth: int,
    max_depth: int,
    max_children: int,
) -> ArtifactNode | None:
    try:
        info = inspect_format(path)
    except Exception:
        return None
    if not _interesting(info):
        return None
    node = _inspect_node(path, depth, max_depth, max_children)
    node.name = display_name
    return node


def _zip_children(path: Path, depth: int, max_depth: int, max_children: int) -> tuple[list[ArtifactNode], list[str]]:
    children: list[ArtifactNode] = []
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix="swf-") as temp_dir:
        for member in archive.infolist():
            if member.is_dir():
                continue
            if len(children) >= max_children:
                warnings.append(f"child limit reached ({max_children})")
                break
            if member.file_size > DEFAULT_MAX_MEMBER_BYTES:
                warnings.append(f"skipped oversized member: {member.filename}")
                continue
            target = Path(temp_dir) / _safe_member_name(member.filename)
            with archive.open(member) as source, target.open("wb") as output:
                remaining = DEFAULT_MAX_MEMBER_BYTES + 1
                while remaining > 0:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    output.write(chunk)
                    remaining -= len(chunk)
            child = _inspect_extracted(target, member.filename, depth + 1, max_depth, max_children)
            if child is not None:
                children.append(child)
    return children, warnings


def _tar_children(path: Path, depth: int, max_depth: int, max_children: int) -> tuple[list[ArtifactNode], list[str]]:
    children: list[ArtifactNode] = []
    warnings: list[str] = []
    with tarfile.open(path, mode="r:*") as archive, tempfile.TemporaryDirectory(prefix="swf-") as temp_dir:
        for member in archive:
            if not member.isfile():
                continue
            if len(children) >= max_children:
                warnings.append(f"child limit reached ({max_children})")
                break
            if member.size > DEFAULT_MAX_MEMBER_BYTES:
                warnings.append(f"skipped oversized member: {member.name}")
                continue
            source = archive.extractfile(member)
            if source is None:
                continue
            target = Path(temp_dir) / _safe_member_name(member.name)
            with source, target.open("wb") as output:
                remaining = DEFAULT_MAX_MEMBER_BYTES + 1
                while remaining > 0:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    output.write(chunk)
                    remaining -= len(chunk)
            child = _inspect_extracted(target, member.name, depth + 1, max_depth, max_children)
            if child is not None:
                children.append(child)
    return children, warnings


def _inspect_node(path: Path, depth: int, max_depth: int, max_children: int) -> ArtifactNode:
    info = inspect_format(path)
    components, findings = analyze_sbom(path, info.format)
    node = ArtifactNode(
        name=path.name,
        format=info.format,
        family=info.family,
        size=path.stat().st_size,
        sha256=_sha256(path),
        metadata=info.metadata,
        components=[component.to_dict() for component in components],
        findings=[finding.to_dict() for finding in findings],
    )
    if depth >= max_depth or not info.container:
        return node
    try:
        if zipfile.is_zipfile(path):
            node.children, node.warnings = _zip_children(path, depth, max_depth, max_children)
        elif tarfile.is_tarfile(path):
            node.children, node.warnings = _tar_children(path, depth, max_depth, max_children)
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        node.warnings.append(f"recursive inspection stopped: {exc}")
    return node


def inspect_artifact(
    path: str | Path,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_children: int = DEFAULT_MAX_CHILDREN,
) -> ArtifactNode:
    """Inspect an artifact and interesting nested artifacts without network access."""
    file_path = Path(path)
    return _inspect_node(file_path, 0, max(0, max_depth), max(1, max_children))
