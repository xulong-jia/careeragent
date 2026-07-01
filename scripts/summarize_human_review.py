#!/usr/bin/env python3
"""Summarize a human review input file without writing raw reviewer data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .import_human_review_proof import build_human_review_proof
except ImportError:  # pragma: no cover - direct script execution path
    from import_human_review_proof import build_human_review_proof


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--batch-id")
    args = parser.parse_args()

    summary = build_human_review_proof(args.input, batch_id=args.batch_id)
    payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(str(args.output))
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
