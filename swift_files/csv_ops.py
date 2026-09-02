"""Inspect, clean, validate, and summarize CSV artifacts."""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .core import SwiftFilezError, atomic_write_text


def _read(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV file into its header and row dictionaries.

    Args:
        path: CSV file to read.

    Returns:
        A pair containing the ordered field names and parsed rows.

    Raises:
        SwiftFilezError: If the file does not exist or has no header row.
    """
    csv_path = Path(path)
    if not csv_path.is_file():
        raise SwiftFilezError(f"CSV file not found: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SwiftFilezError("CSV file has no header row")
        rows = [dict(row) for row in reader]
        return list(reader.fieldnames), rows


def _key(row: dict[str, str], keys: Iterable[str] | None, fieldnames: list[str]) -> tuple:
    """Build the comparison key used for duplicate detection.

    Args:
        row: Parsed CSV row.
        keys: Columns to include, or ``None`` to use every column.
        fieldnames: Valid columns from the CSV header.

    Returns:
        Tuple of cell values in comparison-column order.

    Raises:
        SwiftFilezError: If a requested comparison column is unknown.
    """
    selected = list(keys or fieldnames)
    missing = [key for key in selected if key not in fieldnames]
    if missing:
        raise SwiftFilezError(f"Unknown CSV column(s): {', '.join(missing)}")
    return tuple(row.get(key, "") for key in selected)


def inspect_csv(path: str | Path) -> dict:
    """Return structural and data-quality statistics for a CSV file.

    Args:
        path: CSV file to inspect.

    Returns:
        Mapping containing row and column counts, blank-cell count, and
        duplicate-group statistics.

    Raises:
        SwiftFilezError: If the CSV cannot be read as a headed table.
    """
    fieldnames, rows = _read(path)
    duplicate_groups = find_duplicate_rows(path)
    blank_cells = sum(1 for row in rows for value in row.values() if value is None or not str(value).strip())
    return {
        "path": str(Path(path)),
        "rows": len(rows),
        "columns": fieldnames,
        "column_count": len(fieldnames),
        "blank_cells": blank_cells,
        "duplicate_groups": len(duplicate_groups),
        "duplicate_rows": sum(len(group["row_numbers"]) - 1 for group in duplicate_groups),
    }


def find_duplicate_rows(path: str | Path, keys: Iterable[str] | None = None) -> list[dict]:
    """Find groups of duplicate CSV rows.

    Args:
        path: CSV file to inspect.
        keys: Columns that define equality, or ``None`` for all columns.

    Returns:
        Duplicate groups containing compared values and one-based source row
        numbers, including the header offset.

    Raises:
        SwiftFilezError: If the CSV is invalid or a requested key is unknown.
    """
    fieldnames, rows = _read(path)
    groups: dict[tuple, list[int]] = defaultdict(list)
    for index, row in enumerate(rows, start=2):
        groups[_key(row, keys, fieldnames)].append(index)
    return [{"values": list(key), "row_numbers": indices} for key, indices in groups.items() if len(indices) > 1]


def _serialize(fieldnames: list[str], rows: list[dict[str, str]]) -> str:
    """Serialize row dictionaries as CSV text.

    Args:
        fieldnames: Output header order.
        rows: Rows to serialize.

    Returns:
        CSV-formatted text including a header row.
    """
    from io import StringIO

    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def dedupe_csv(path: str | Path, output: str | Path, keys: Iterable[str] | None = None, keep: str = "first") -> dict:
    """Write a CSV with duplicate rows removed.

    Args:
        path: Source CSV file.
        output: Destination for the deduplicated CSV.
        keys: Columns that define duplicates, or ``None`` for all columns.
        keep: Duplicate survivor policy, either ``"first"`` or ``"last"``.

    Returns:
        Summary of input/output row counts, removed rows, key columns, and
        destination path.

    Raises:
        SwiftFilezError: If ``keep`` is invalid, the CSV is invalid, or a key
            column is unknown.
    """
    if keep not in {"first", "last"}:
        raise SwiftFilezError("keep must be 'first' or 'last'")
    fieldnames, rows = _read(path)
    selected_keys = list(keys or fieldnames)
    if keep == "first":
        seen: set[tuple] = set()
        kept: list[dict[str, str]] = []
        for row in rows:
            row_key = _key(row, selected_keys, fieldnames)
            if row_key in seen:
                continue
            seen.add(row_key)
            kept.append(row)
    else:
        seen = set()
        reversed_kept: list[dict[str, str]] = []
        for row in reversed(rows):
            row_key = _key(row, selected_keys, fieldnames)
            if row_key in seen:
                continue
            seen.add(row_key)
            reversed_kept.append(row)
        kept = list(reversed(reversed_kept))
    atomic_write_text(output, _serialize(fieldnames, kept))
    return {
        "input_rows": len(rows),
        "output_rows": len(kept),
        "removed": len(rows) - len(kept),
        "output": str(Path(output)),
        "keys": selected_keys,
        "keep": keep,
    }


def sort_csv(path: str | Path, output: str | Path, column: str, reverse: bool = False) -> dict:
    """Sort CSV rows case-insensitively by one column and write the result.

    Args:
        path: Source CSV file.
        output: Destination CSV file.
        column: Column whose text values determine ordering.
        reverse: Whether to sort in descending order.

    Returns:
        Summary containing the row count, sort column, direction, and output.

    Raises:
        SwiftFilezError: If the CSV is invalid or ``column`` is unknown.
    """
    fieldnames, rows = _read(path)
    if column not in fieldnames:
        raise SwiftFilezError(f"Unknown CSV column: {column}")
    sorted_rows = sorted(rows, key=lambda row: (row.get(column) or "").casefold(), reverse=reverse)
    atomic_write_text(output, _serialize(fieldnames, sorted_rows))
    return {"rows": len(rows), "column": column, "reverse": reverse, "output": str(Path(output))}


def validate_csv(path: str | Path, required_columns: Iterable[str]) -> dict:
    """Validate required CSV columns and nonblank required values.

    Args:
        path: CSV file to validate.
        required_columns: Columns that must exist and be populated per row.

    Returns:
        Validation report with an ``ok`` flag, missing columns, and rows with
        blank required values.

    Raises:
        SwiftFilezError: If the CSV itself cannot be read.
    """
    fieldnames, rows = _read(path)
    required = list(required_columns)
    missing_columns = [column for column in required if column not in fieldnames]
    blank_required: list[dict] = []
    if not missing_columns:
        for index, row in enumerate(rows, start=2):
            missing_values = [column for column in required if not (row.get(column) or "").strip()]
            if missing_values:
                blank_required.append({"row": index, "columns": missing_values})
    return {
        "ok": not missing_columns and not blank_required,
        "rows": len(rows),
        "missing_columns": missing_columns,
        "blank_required": blank_required,
    }


def summarize_csv(path: str | Path, group_by: str, sum_columns: Iterable[str]) -> dict:
    """Aggregate numeric CSV columns by a grouping column.

    Currency symbols and commas are stripped before decimal conversion. Blank
    numeric cells are ignored; malformed numeric values are reported rather
    than silently included in totals.

    Args:
        path: CSV file to summarize.
        group_by: Column whose values define aggregation groups.
        sum_columns: Numeric columns to total within each group.

    Returns:
        Mapping containing grouped decimal totals serialized as strings and a
        list of cells that could not be parsed as numbers.

    Raises:
        SwiftFilezError: If the CSV is invalid or requested columns are absent.
    """
    fieldnames, rows = _read(path)
    sum_cols = list(sum_columns)
    missing = [column for column in [group_by, *sum_cols] if column not in fieldnames]
    if missing:
        raise SwiftFilezError(f"Unknown CSV column(s): {', '.join(missing)}")
    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: {column: Decimal("0") for column in sum_cols})
    invalid_cells: list[dict] = []
    for index, row in enumerate(rows, start=2):
        group = (row.get(group_by) or "").strip() or "(blank)"
        for column in sum_cols:
            raw = (row.get(column) or "").strip().replace(",", "").replace("$", "")
            if not raw:
                continue
            try:
                totals[group][column] += Decimal(raw)
            except InvalidOperation:
                invalid_cells.append({"row": index, "column": column, "value": row.get(column)})
    groups = [
        {group_by: group, **{column: str(value) for column, value in values.items()}}
        for group, values in sorted(totals.items())
    ]
    return {"group_by": group_by, "sum_columns": sum_cols, "groups": groups, "invalid_cells": invalid_cells}
