import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from swift_files.cli import app

runner = CliRunner()


def _release_with_sbom(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "sbom/bom.cdx.json",
            json.dumps(
                {
                    "bomFormat": "CycloneDX",
                    "specVersion": "1.6",
                    "components": [
                        {
                            "type": "library",
                            "name": "requests",
                            "version": "2.32.0",
                            "purl": "pkg:pypi/requests@2.32.0",
                        }
                    ],
                }
            ),
        )


def test_primary_inspect_reports_artifact_format(tmp_path: Path):
    path = tmp_path / "package.json"
    path.write_text('{"name":"demo"}', encoding="utf-8")
    result = runner.invoke(app, ["inspect", str(path), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["artifact"]["format"] == "npm-manifest"
    assert payload["artifact"]["family"] == "dependency-manifest"


def test_primary_inspect_recurses_into_sbom(tmp_path: Path):
    path = tmp_path / "release.zip"
    _release_with_sbom(path)
    result = runner.invoke(app, ["inspect", str(path), "--recursive", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["artifacts"] == 2
    assert payload["summary"]["components"] == 1
    assert payload["children"][0]["family"] == "sbom"


def test_formats_is_available_on_primary_cli():
    result = runner.invoke(app, ["formats", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "cyclonedx-sbom" in payload
    assert "oci-image-layout" in payload


def test_policy_accepts_compliant_release(tmp_path: Path):
    artifact = tmp_path / "release.zip"
    _release_with_sbom(artifact)
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "require_families": ["sbom"],
                "require_component_versions": True,
                "require_component_purls": True,
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["policy", "check", str(artifact), "--policy", str(policy), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["ok"] is True


def test_policy_rejection_uses_ci_friendly_exit_code(tmp_path: Path):
    artifact = tmp_path / "release.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("README.txt", "no sbom here")
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"require_families": ["sbom"]}), encoding="utf-8")
    result = runner.invoke(app, ["policy", "check", str(artifact), "--policy", str(policy), "--json"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["violations"][0]["code"] == "required-family-missing"


def test_readiness_reports_beta_uat_ready():
    result = runner.invoke(app, ["readiness", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["uat_ready"] is True
    assert payload["policy_enforcement"] is True
    assert payload["core_offline"] is True
