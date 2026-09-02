"""Normalized local artifact intelligence analyzers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

MAX_SBOM_BYTES = 16 * 1024 * 1024
MAX_COMPONENTS = 5000


@dataclass(frozen=True)
class Component:
    """Represent Component."""
    name: str
    version: str | None = None
    component_type: str | None = None
    purl: str | None = None
    license: str | None = None
    source: str | None = None

    def to_dict(self) -> dict:
        """Handle to dict.

        Returns:
            Function result.
        """
        return asdict(self)


@dataclass(frozen=True)
class Finding:
    """Represent Finding."""
    code: str
    category: str
    severity: str
    message: str
    evidence: dict

    def to_dict(self) -> dict:
        """Handle to dict.

        Returns:
            Function result.
        """
        return asdict(self)


def _license_name(value: object) -> str | None:
    """Handle license name.

    Args:
        value: Function argument.

    Returns:
        Function result.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        license_value = value.get("license")
        if isinstance(license_value, dict):
            return license_value.get("id") or license_value.get("name")
        return value.get("expression") or value.get("id") or value.get("name")
    return None


def _read_json(path: Path) -> dict | None:
    """Handle read json.

    Args:
        path: Function argument.

    Returns:
        Function result.
    """
    try:
        if path.stat().st_size > MAX_SBOM_BYTES:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _cyclonedx_components(payload: dict, source: str) -> list[Component]:
    """Handle cyclonedx components.

    Args:
        payload: Function argument.
        source: Function argument.

    Returns:
        Function result.
    """
    result: list[Component] = []
    for item in payload.get("components", [])[:MAX_COMPONENTS]:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        licenses = item.get("licenses") or []
        license_name = _license_name(licenses[0]) if licenses else None
        result.append(
            Component(
                name=str(item["name"]),
                version=str(item["version"]) if item.get("version") is not None else None,
                component_type=str(item["type"]) if item.get("type") else None,
                purl=str(item["purl"]) if item.get("purl") else None,
                license=license_name,
                source=source,
            )
        )
    return result


def _spdx_components(payload: dict, source: str) -> list[Component]:
    """Handle spdx components.

    Args:
        payload: Function argument.
        source: Function argument.

    Returns:
        Function result.
    """
    result: list[Component] = []
    for item in payload.get("packages", [])[:MAX_COMPONENTS]:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        purl = None
        for ref in item.get("externalRefs", []):
            if isinstance(ref, dict) and str(ref.get("referenceType", "")).lower().endswith("purl"):
                purl = ref.get("referenceLocator")
                break
        result.append(
            Component(
                name=str(item["name"]),
                version=str(item["versionInfo"]) if item.get("versionInfo") is not None else None,
                component_type="package",
                purl=str(purl) if purl else None,
                license=item.get("licenseConcluded") or item.get("licenseDeclared"),
                source=source,
            )
        )
    return result


def analyze_sbom(path: str | Path, artifact_format: str) -> tuple[list[Component], list[Finding]]:
    """Extract normalized components and useful quality findings from JSON SBOMs."""
    file_path = Path(path)
    payload = _read_json(file_path)
    if payload is None:
        if artifact_format in {"cyclonedx-sbom", "spdx-sbom"}:
            return [], [
                Finding(
                    code="sbom-unreadable",
                    category="sbom-quality",
                    severity="warning",
                    message="SBOM could not be fully parsed within Swift safety limits.",
                    evidence={"path": file_path.name, "max_bytes": MAX_SBOM_BYTES},
                )
            ]
        return [], []

    if artifact_format == "cyclonedx-sbom":
        components = _cyclonedx_components(payload, file_path.name)
    elif artifact_format == "spdx-sbom":
        components = _spdx_components(payload, file_path.name)
    else:
        return [], []

    findings: list[Finding] = [
        Finding(
            code="sbom-components",
            category="inventory",
            severity="info",
            message=f"SBOM declares {len(components)} normalized components.",
            evidence={"component_count": len(components), "format": artifact_format},
        )
    ]
    missing_versions = sum(1 for component in components if not component.version)
    missing_purls = sum(1 for component in components if not component.purl)
    if missing_versions:
        findings.append(
            Finding(
                code="sbom-missing-versions",
                category="sbom-quality",
                severity="warning",
                message=f"{missing_versions} SBOM components do not declare a version.",
                evidence={"missing_versions": missing_versions, "component_count": len(components)},
            )
        )
    if missing_purls:
        findings.append(
            Finding(
                code="sbom-missing-purls",
                category="sbom-quality",
                severity="info",
                message=f"{missing_purls} SBOM components do not declare a package URL (purl).",
                evidence={"missing_purls": missing_purls, "component_count": len(components)},
            )
        )
    return components, findings
