"""Document this first-party Python module."""
from typer.testing import CliRunner

from swift_files.app import app

runner = CliRunner()


def test_version():
    """Verify version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0 and "SwiftFilez 0.4.0" in result.stdout


def test_doctor_json():
    """Verify doctor json."""
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0 and '"ok": true' in result.stdout.lower()


def test_manifest_verify_exit_code_on_drift(tmp_path):
    """Verify manifest verify exit code on drift.

    Args:
        tmp_path: Function argument.
    """
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.txt").write_text("one", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    build = runner.invoke(app, ["manifest", "build", str(root), "--output", str(manifest)])
    assert build.exit_code == 0
    (root / "a.txt").write_text("changed", encoding="utf-8")
    verify = runner.invoke(app, ["manifest", "verify", str(manifest), "--root", str(root), "--json"])
    assert verify.exit_code == 2 and '"ok": false' in verify.stdout.lower()
