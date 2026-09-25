"""Provenance tracking, canonical serialization, and deterministic hashing for MKE."""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List
from pydantic import BaseModel


def canonical_json_dumps(obj: Any) -> str:
    """Serialize any data structure to a canonical, deterministic JSON string.

    Guarantees:
    - Sorted dictionary keys.
    - Consistent 2-space indentation or compact separators.
    - Deterministic float/number string formatting.
    - No trailing whitespace.
    - UTF-8 characters preserved without unneeded ASCII escaping.
    """
    if isinstance(obj, BaseModel):
        data = obj.model_dump(mode="json")
    elif isinstance(obj, dict):
        data = obj
    else:
        data = obj

    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ": "),
    )


def compute_content_sha256(data: str | bytes) -> str:
    """Compute SHA-256 digest over normalized text or binary bytes."""
    if isinstance(data, str):
        # Normalize Windows CRLF to LF to maintain cross-platform hash identity
        normalized = data.replace("\r\n", "\n").encode("utf-8")
    else:
        normalized = data
    return hashlib.sha256(normalized).hexdigest()


def compute_file_sha256(file_path: Path | str) -> str:
    """Compute SHA-256 hash of a file on disk with LF line ending normalization."""
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    text = p.read_text(encoding="utf-8")
    return compute_content_sha256(text)


def write_canonical_jsonl(
    output_path: Path | str,
    records: Iterable[BaseModel | Dict[str, Any]],
    sort_key_attr: str = "",
) -> int:
    """Write records to a canonical JSONL file with stable sorting and key ordering.

    Args:
        output_path: Target path to write JSONL.
        records: Iterable of Pydantic models or dicts.
        sort_key_attr: Optional attribute or dict key to sort records deterministically.

    Returns:
        Number of records written.
    """
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    items = list(records)
    if sort_key_attr:
        def get_key(item: Any) -> str:
            if isinstance(item, BaseModel):
                return str(getattr(item, sort_key_attr, ""))
            if isinstance(item, dict):
                return str(item.get(sort_key_attr, ""))
            return ""
        items.sort(key=get_key)

    lines = []
    for item in items:
        line = canonical_json_dumps(item)
        lines.append(line)

    content = "\n".join(lines) + ("\n" if lines else "")
    p.write_text(content, encoding="utf-8", newline="\n")
    return len(items)


def read_jsonl(input_path: Path | str) -> List[Dict[str, Any]]:
    """Read a JSONL file and return list of dictionaries."""
    p = Path(input_path)
    if not p.is_file():
        raise FileNotFoundError(f"JSONL file not found: {p}")

    results = []
    for line_num, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            results.append(json.loads(stripped))
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON on line {line_num} of {p}: {e}")
    return results
