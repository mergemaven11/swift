"""Small, offline policy engine for artifact acceptance gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .artifacts import ArtifactNode
from .core import SwiftFilezError


@dataclass(frozen=True)
class PolicyResult:
    ok: bool
    violations: list[dict]
    checks: dict

    def to_dict(self) -> dict:
        return {"ok": self.ok, "violations": self.violations, "checks": self.checks}


def load_policy(path: str | Path) -> dict:
    policy_path = Path(path)
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SwiftFilezError(f"unable to load policy {policy_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SwiftFilezError("policy must be a JSON object")
    return payload


def _walk(node: ArtifactNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def evaluate_policy(root: ArtifactNode, policy: dict) -> PolicyResult:
    """Evaluate deterministic local acceptance rules against an artifact tree."""
    nodes = list(_walk(root))
    families = {node.family for node in nodes}
    components = [component for node in nodes for component in node.components]
    findings = [finding for node in nodes for finding in node.findings]
    warnings = [warning for node in nodes for warning in node.warnings]
    violations: list[dict] = []

    required_families = set(policy.get("require_families", []))
    for family in sorted(required_families - families):
        violations.append(
            {"code": "required-family-missing", "message": f"required artifact family not found: {family}"}
        )

    denied_families = set(policy.get("deny_families", []))
    for family in sorted(denied_families & families):
        violations.append({"code": "denied-family-found", "message": f"denied artifact family found: {family}"})

    if policy.get("require_component_versions"):
        missing = sum(1 for component in components if not component.get("version"))
        if missing:
            violations.append(
                {"code": "component-version-missing", "message": f"{missing} component(s) have no version"}
            )

    if policy.get("require_component_purls"):
        missing = sum(1 for component in components if not component.get("purl"))
        if missing:
            violations.append({"code": "component-purl-missing", "message": f"{missing} component(s) have no purl"})

    max_findings = policy.get("max_findings")
    if isinstance(max_findings, int) and len(findings) > max_findings:
        violations.append(
            {
                "code": "too-many-findings",
                "message": f"{len(findings)} findings exceeds policy maximum of {max_findings}",
            }
        )

    if policy.get("fail_on_warnings") and warnings:
        violations.append(
            {"code": "artifact-warnings", "message": f"artifact inspection produced {len(warnings)} warning(s)"}
        )

    checks = {
        "artifacts": len(nodes),
        "families": sorted(families),
        "components": len(components),
        "findings": len(findings),
        "warnings": len(warnings),
        "rules": len(policy),
    }
    return PolicyResult(ok=not violations, violations=violations, checks=checks)
