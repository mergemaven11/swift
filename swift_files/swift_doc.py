"""Generic artifact compatibility layer."""

from .core import FileRecord, SwiftFilezError, hash_file, inspect_file, safe_copy

__all__ = ["FileRecord", "SwiftFilezError", "hash_file", "inspect_file", "safe_copy"]
