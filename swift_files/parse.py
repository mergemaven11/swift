"""Compatibility wrapper for the original argparse prototype.

The supported CLI now lives in :mod:`swift_files.app` and is installed as ``swf``.
"""
from .app import app, main

__all__ = ["app", "main"]
