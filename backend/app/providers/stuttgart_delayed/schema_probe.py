"""Read-only schema inspection for official Börse Stuttgart delayed JSON.gz files.

This module deliberately does not infer or activate production mappings. It helps an
operator inspect the structural shape of one official XSTU pre-trade payload without
persisting market data or printing quote values.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RecordArrayCandidate:
    """Structural summary for a JSON array that appears to contain object records."""

    path: str
    item_count: int
    object_count: int
    leaf_paths: tuple[str, ...]
    leaf_types: tuple[tuple[str, tuple[str, ...]], ...]


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _flatten_leaf_types(
    value: Any,
    *,
    prefix: str = "",
    max_depth: int = 8,
) -> dict[str, set[str]]:
    if max_depth < 0:
        return {}
    if isinstance(value, dict):
        flattened: dict[str, set[str]] = {}
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            child_types = _flatten_leaf_types(
                child,
                prefix=child_path,
                max_depth=max_depth - 1,
            )
            for path, types in child_types.items():
                flattened.setdefault(path, set()).update(types)
        return flattened
    return {prefix or "$": {_type_name(value)}}


def discover_record_arrays(
    payload: Any,
    *,
    sample_records: int = 50,
    max_depth: int = 6,
) -> tuple[RecordArrayCandidate, ...]:
    """Return candidate object-record arrays ordered by path.

    Only structural information is retained. Concrete values are intentionally omitted.
    """

    candidates: list[RecordArrayCandidate] = []

    def visit(value: Any, *, path: str, depth: int) -> None:
        if depth > max_depth:
            return
        if isinstance(value, list):
            object_items = [item for item in value if isinstance(item, dict)]
            if object_items:
                observed: dict[str, set[str]] = {}
                for item in object_items[:sample_records]:
                    for leaf_path, types in _flatten_leaf_types(item).items():
                        observed.setdefault(leaf_path, set()).update(types)
                candidates.append(
                    RecordArrayCandidate(
                        path=path,
                        item_count=len(value),
                        object_count=len(object_items),
                        leaf_paths=tuple(sorted(observed)),
                        leaf_types=tuple(
                            (leaf_path, tuple(sorted(types)))
                            for leaf_path, types in sorted(observed.items())
                        ),
                    )
                )
            for index, item in enumerate(value[:3]):
                visit(item, path=f"{path}[{index}]", depth=depth + 1)
            return
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = str(key) if path == "$" else f"{path}.{key}"
                visit(child, path=child_path, depth=depth + 1)

    visit(payload, path="$", depth=0)
    return tuple(sorted(candidates, key=lambda candidate: candidate.path))


def candidate_field_hints(
    candidate: RecordArrayCandidate,
) -> dict[str, tuple[str, ...]]:
    """Return name-based candidate paths without declaring any mapping verified."""

    keywords = {
        "isin": ("isin",),
        "mic": ("mic", "venue"),
        "side": ("side", "bidask", "direction"),
        "price": ("price", "px"),
        "currency": ("currency", "ccy"),
        "timestamp": ("timestamp", "time", "observed", "date"),
    }
    hints: dict[str, tuple[str, ...]] = {}
    for category, terms in keywords.items():
        matches = tuple(
            path for path in candidate.leaf_paths if any(term in path.lower() for term in terms)
        )
        if matches:
            hints[category] = matches
    return hints


def load_gzipped_json(path: Path) -> Any:
    """Load one local official JSON.gz payload for structural inspection."""

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def render_report(payload: Any) -> str:
    """Render a deterministic structural report with no market-data values."""

    candidates = discover_record_arrays(payload)
    lines = [
        f"top_level_type={_type_name(payload)}",
        f"record_array_candidates={len(candidates)}",
    ]
    for index, candidate in enumerate(candidates, start=1):
        lines.append("")
        lines.append(f"candidate[{index}].path={candidate.path}")
        lines.append(f"candidate[{index}].items={candidate.item_count}")
        lines.append(f"candidate[{index}].objects={candidate.object_count}")
        lines.append(f"candidate[{index}].leaf_paths={len(candidate.leaf_paths)}")
        type_counts = Counter(type_name for _, types in candidate.leaf_types for type_name in types)
        lines.append(
            f"candidate[{index}].leaf_type_counts="
            + ",".join(f"{name}:{count}" for name, count in sorted(type_counts.items()))
        )
        for path, types in candidate.leaf_types:
            lines.append(f"  {path}: {'|'.join(types)}")
        hints = candidate_field_hints(candidate)
        for category, paths in sorted(hints.items()):
            lines.append(f"candidate[{index}].hint.{category}=" + ",".join(paths))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the structure of one official Börse Stuttgart XSTU pre-trade JSON.gz "
            "without printing quote values or changing application configuration."
        )
    )
    parser.add_argument(
        "payload",
        type=Path,
        help="Path to an official XSTU-pretrade-*.json.gz file",
    )
    args = parser.parse_args(argv)
    payload = load_gzipped_json(args.payload)
    print(render_report(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
