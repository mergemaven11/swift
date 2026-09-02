"""Document this first-party Python module."""

from swift_files.config import load_settings


def test_env_config(monkeypatch, tmp_path):
    """Verify env config.

    Args:
        monkeypatch: Function argument.
        tmp_path: Function argument.
    """
    monkeypatch.setenv("SWIFTFILEZ_WORKERS", "7")
    monkeypatch.setenv("SWIFTFILEZ_HASH_ALGORITHM", "sha512")
    monkeypatch.setenv("SWIFTFILEZ_QUARANTINE_DIR", str(tmp_path / "q"))
    settings = load_settings()
    assert settings.workers == 7 and settings.hash_algorithm == "sha512" and settings.quarantine_dir == tmp_path / "q"
