"""Runtime configuration for SwiftFilez.

Settings are loaded from environment variables with conservative defaults so
CLI and CI behavior stays predictable across developer machines and automation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_HASH = "SWIFTFILEZ_HASH_ALGORITHM"
ENV_WORKERS = "SWIFTFILEZ_WORKERS"
ENV_QUARANTINE = "SWIFTFILEZ_QUARANTINE_DIR"


@dataclass(frozen=True)
class Settings:
    """Resolved SwiftFilez runtime settings.

    Attributes:
        hash_algorithm: Hashlib-compatible algorithm used for file integrity.
        workers: Maximum worker count for concurrent file operations.
        quarantine_dir: Directory used when duplicate quarantine is requested.
    """

    hash_algorithm: str = "sha256"
    workers: int = 4
    quarantine_dir: Path = Path(".swiftfilez-quarantine")


def load_settings() -> Settings:
    """Load SwiftFilez settings from environment variables.

    Worker counts are clamped to the supported range of 1 through 32. Invalid
    worker values fall back to four workers instead of preventing the CLI from
    starting.

    Returns:
        A frozen ``Settings`` instance with normalized runtime values.
    """
    workers_raw = os.getenv(ENV_WORKERS, "4")
    try:
        workers = max(1, min(32, int(workers_raw)))
    except ValueError:
        workers = 4
    return Settings(
        hash_algorithm=os.getenv(ENV_HASH, "sha256").lower(),
        workers=workers,
        quarantine_dir=Path(os.getenv(ENV_QUARANTINE, ".swiftfilez-quarantine")).expanduser(),
    )
