"""Runtime configuration for SwiftFilez."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_HASH = "SWIFTFILEZ_HASH_ALGORITHM"
ENV_WORKERS = "SWIFTFILEZ_WORKERS"
ENV_QUARANTINE = "SWIFTFILEZ_QUARANTINE_DIR"


@dataclass(frozen=True)
class Settings:
    hash_algorithm: str = "sha256"
    workers: int = 4
    quarantine_dir: Path = Path(".swiftfilez-quarantine")


def load_settings() -> Settings:
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
