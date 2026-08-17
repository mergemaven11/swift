import csv
from swift_files.csv_ops import dedupe_csv, find_duplicate_rows, inspect_csv, sort_csv, summarize_csv, validate_csv


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["customer", "credit", "debit", "status"])
        writer.writeheader(); writer.writerows(rows)


def sample_rows():
    return [
        {"customer": "A", "credit": "100", "debit": "20", "status": "ok"},
        {"customer": "A", "credit": "100", "debit": "20", "status": "ok"},
        {"customer": "B", "credit": "50", "debit": "10", "status": ""},
    ]


def test_csv_inspect_and_duplicates(tmp_path):
    path = tmp_path / "data.csv"; write_csv(path, sample_rows())
    info = inspect_csv(path); assert info["rows"] == 3; assert info["duplicate_rows"] == 1
    groups = find_duplicate_rows(path, ["customer", "credit", "debit", "status"])
    assert groups[0]["row_numbers"] == [2, 3]


def test_csv_dedupe(tmp_path):
    path = tmp_path / "data.csv"; out = tmp_path / "clean.csv"; write_csv(path, sample_rows())
    result = dedupe_csv(path, out)
    assert result["removed"] == 1
    assert inspect_csv(out)["rows"] == 2


def test_csv_dedupe_by_key(tmp_path):
    path = tmp_path / "data.csv"; out = tmp_path / "clean.csv"; rows = sample_rows(); rows[1]["credit"] = "999"; write_csv(path, rows)
    result = dedupe_csv(path, out, ["customer"], keep="last")
    assert result["removed"] == 1
    with out.open("r", encoding="utf-8") as handle: data = list(csv.DictReader(handle))
    assert data[0]["credit"] == "999"


def test_csv_sort(tmp_path):
    path = tmp_path / "data.csv"; out = tmp_path / "sorted.csv"; write_csv(path, list(reversed(sample_rows())))
    sort_csv(path, out, "customer")
    with out.open("r", encoding="utf-8") as handle: rows = list(csv.DictReader(handle))
    assert rows[0]["customer"] == "A" and rows[-1]["customer"] == "B"


def test_csv_validate(tmp_path):
    path = tmp_path / "data.csv"; write_csv(path, sample_rows())
    result = validate_csv(path, ["customer", "status"])
    assert result["ok"] is False
    assert result["blank_required"] == [{"row": 4, "columns": ["status"]}]


def test_csv_summarize(tmp_path):
    path = tmp_path / "data.csv"; write_csv(path, sample_rows())
    result = summarize_csv(path, "customer", ["credit", "debit"])
    groups = {row["customer"]: row for row in result["groups"]}
    assert groups["A"]["credit"] == "200" and groups["A"]["debit"] == "40" and groups["B"]["credit"] == "50"
