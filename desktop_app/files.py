"""Bounded UTF-8 inputs and lossless, formula-protected tabular output."""
from __future__ import annotations

import csv
import hashlib
import io
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
csv.field_size_limit(MAX_BYTES)


class FileError(ValueError):
    pass


def load_upload(path) -> dict:
    path = Path(path)
    kind = path.suffix.lower().lstrip(".")
    if kind not in {"txt", "csv"}:
        raise FileError("只支援單一 TXT／CSV 檔。")
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError:
        raise FileError("無法讀取檔案，請確認路徑與權限。") from None
    if len(raw) > MAX_BYTES:
        raise FileError("檔案超過 2 MiB，沒有截斷讀取。")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise FileError("請先將檔案轉為 UTF-8／UTF-8 BOM。") from None
    if "\x00" in text:
        raise FileError("檔案包含 NUL，請改存純文字。")
    result = {"name": path.name, "kind": kind, "text": text, "sha256": hashlib.sha256(raw).hexdigest()}
    if kind == "txt":
        if len(text) > 50000:
            raise FileError("文字超過 50,000 字元，沒有截斷處理。")
        result["preview"] = text[:2000]
        return result
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        columns = next(reader, [])
        if not columns or len(columns) > 100 or any(not c.strip() for c in columns):
            raise FileError("CSV 需有非空白標題，且最多 100 欄。")
        if len(set(c.strip() for c in columns)) != len(columns):
            raise FileError("CSV 標題不可重複。")
        rows = []
        for row in reader:
            if len(row) != len(columns):
                raise FileError("CSV 每列欄位數需與標題一致；空白列也需補正。")
            rows.append(row)
            if len(rows) > 10000:
                raise FileError("CSV 超過 10,000 資料列。")
    except csv.Error:
        raise FileError("CSV 格式錯誤或單欄過長，請補正。") from None
    preview = io.StringIO(newline="")
    writer = csv.writer(preview)
    writer.writerow(columns)
    writer.writerows(rows[:20])
    result.update(columns=columns, rows=rows, preview=preview.getvalue(),
                  metadata={"row_count": len(rows), "column_count": len(columns),
                            "empty_cells": sum(v == "" for row in rows for v in row)})
    return result


def _cell(value, column, tsv):
    if value is None:
        return "", 0
    kind = column.get("type", "text")
    if isinstance(value, (dict, list, bool, float)):
        raise FileError("欄位型態錯誤；浮點數需在資料來源轉為精確十進位字串。")
    text = str(value)
    if "\x00" in text or (tsv and any(c in text for c in "\t\r\n")):
        raise FileError("欄名或資料含特殊分隔字元，請改用 CSV；NUL 必須先修正。")
    if kind in {"integer", "decimal", "number"}:
        pattern = r"[+-]?\d+" if kind == "integer" else r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
        if not re.fullmatch(pattern, text):
            raise FileError("數值欄含無效數值，不可略過公式防護。")
        try:
            if not Decimal(text).is_finite():
                raise InvalidOperation()
        except InvalidOperation:
            raise FileError("數值欄需為有限且有效數值。") from None
        return text, 0
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text, 1
    return text, 0


def _render(result, selected_indices, include_headers, tsv):
    columns, rows = result["columns"], result["rows"]
    if selected_indices is None:
        selected_indices = range(len(rows))
    selected_indices = list(selected_indices)
    if (any(type(i) is not int or not 0 <= i < len(rows) for i in selected_indices)
            or len(selected_indices) != len(set(selected_indices))):
        raise FileError("選取列已失效或重複，請重新選取。")
    output, protected = [], 0
    if include_headers:
        values = [_cell(c.get("label", c["name"]), {"type": "text"}, tsv) for c in columns]
        output.append([v for v, _ in values])
        protected += sum(p for _, p in values)
    for i in selected_indices:
        if len(rows[i]) != len(columns):
            raise FileError("結果欄位數不一致。")
        values = [_cell(v, c, tsv) for v, c in zip(rows[i], columns)]
        output.append([v for v, _ in values])
        protected += sum(p for _, p in values)
    if tsv:
        return "\r\n".join("\t".join(row) for row in output), protected
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\r\n").writerows(output)
    return stream.getvalue(), protected


def render_tsv(result, selected_indices=None, include_headers=True):
    return _render(result, selected_indices, include_headers, True)


def render_csv(result, selected_indices=None, include_headers=True):
    """Return Unicode CSV; caller writes it using encoding='utf-8-sig'."""
    return _render(result, selected_indices, include_headers, False)[0]
