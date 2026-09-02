"""Document this first-party Python module."""

import json
from pathlib import Path

from swift_files.artifacts import inspect_artifact
from swift_files.intelligence import analyze_sbom


def test_cyclonedx_components_are_normalized(tmp_path: Path):
    """Verify cyclonedx components are normalized.

    Args:
        tmp_path: Function argument.
    """
    path = tmp_path / "bom.cdx.json"
    path.write_text(
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
                        "licenses": [{"license": {"id": "Apache-2.0"}}],
                    },
                    {"type": "library", "name": "mystery-lib"},
                ],
            }
        ),
        encoding="utf-8",
    )

    components, findings = analyze_sbom(path, "cyclonedx-sbom")

    assert len(components) == 2
    assert components[0].name == "requests"
    assert components[0].purl == "pkg:pypi/requests@2.32.0"
    assert components[0].license == "Apache-2.0"
    assert any(finding.code == "sbom-missing-versions" for finding in findings)
    assert any(finding.code == "sbom-missing-purls" for finding in findings)


def test_spdx_packages_are_normalized(tmp_path: Path):
    """Verify spdx packages are normalized.

    Args:
        tmp_path: Function argument.
    """
    path = tmp_path / "inventory.spdx.json"
    path.write_text(
        json.dumps(
            {
                "spdxVersion": "SPDX-2.3",
                "packages": [
                    {
                        "name": "flask",
                        "versionInfo": "3.0.0",
                        "licenseDeclared": "BSD-3-Clause",
                        "externalRefs": [
                            {
                                "referenceType": "purl",
                                "referenceLocator": "pkg:pypi/flask@3.0.0",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    components, findings = analyze_sbom(path, "spdx-sbom")

    assert components[0].name == "flask"
    assert components[0].version == "3.0.0"
    assert components[0].license == "BSD-3-Clause"
    assert findings[0].code == "sbom-components"


def test_artifact_summary_rolls_up_nested_sbom_intelligence(tmp_path: Path):
    """Verify artifact summary rolls up nested sbom intelligence.

    Args:
        tmp_path: Function argument.
    """
    import zipfile

    outer = tmp_path / "release.zip"
    with zipfile.ZipFile(outer, "w") as archive:
        archive.writestr(
            "sbom/bom.cdx.json",
            json.dumps(
                {
                    "bomFormat": "CycloneDX",
                    "specVersion": "1.6",
                    "components": [{"type": "library", "name": "demo", "version": "1.0"}],
                }
            ),
        )

    payload = inspect_artifact(outer).to_dict()

    assert payload["summary"]["artifacts"] == 2
    assert payload["summary"]["components"] == 1
    assert payload["summary"]["findings"] >= 1
    assert payload["summary"]["families"]["sbom"] == 1
