"""Explicit offline file adapter for Hebeltrader research source preparation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from app.features.learning.application.research_preparation import prepare_research_files
from app.features.learning.application.research_preparation_parsing import parse_date
from app.features.learning.domain.research_preparation import PreparationError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Expliziter JSON-Quellensnapshot")
    parser.add_argument(
        "--out", type=Path, required=True, help="Neuer, noch nicht existierender Ordner"
    )
    parser.add_argument("--cutoff", required=True, help="Separater Forschungsstichtag YYYY-MM-DD")
    parser.add_argument("--expected-count", type=int, required=True, help="Explizite Sollanzahl")
    args = parser.parse_args(argv)
    try:
        bundle = prepare_research_files(
            input_path=args.input,
            output_dir=args.out,
            cutoff=parse_date(args.cutoff, field="cutoff"),
            expected_count=args.expected_count,
        )
    except PreparationError as exc:
        print(
            json.dumps({"status": "REJECTED", "code": exc.code, "detail": str(exc)}),
            file=sys.stderr,
        )
        return 2
    except OSError as exc:
        print(
            json.dumps({"status": "REJECTED", "code": "FILE_IO_ERROR", "detail": str(exc)}),
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {
                "status": bundle.manifest["status"],
                "case_count": bundle.manifest["case_count"],
                "source_status_counts": bundle.manifest["source_status_counts"],
                "historical_result_status": bundle.manifest["historical_result_status"],
                "output": str(args.out),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
