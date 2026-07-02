#!/usr/bin/env python3
"""Create template-only external ops proof files.

The output is a starting point for private evidence collection. It is not real
deployment, backup, monitoring or security proof.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "evidence" / "templates"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence" / "private_outputs"
OPS_PROOF_TYPES = ("deployment", "backup_purge", "monitoring", "security_review")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_ops_template(proof_type: str, *, generated_at: str | None = None) -> dict[str, Any]:
    if proof_type not in OPS_PROOF_TYPES:
        raise ValueError(f"unsupported ops proof type: {proof_type}")
    path = TEMPLATE_DIR / f"{proof_type}_proof.template.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["created_at"] = generated_at or datetime.now(timezone.utc).isoformat()
    payload["proof_id"] = f"{proof_type}-proof-template-{generated_at or _timestamp()}"
    payload["template_only"] = True
    payload["production_quality_candidate_signal"] = False
    limitations = list(payload.get("limitations") or [])
    if "template_only" not in limitations:
        limitations.insert(0, "template_only")
    payload["limitations"] = limitations
    return payload


def write_ops_templates(
    proof_types: list[str],
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    generated_at: str | None = None,
    dry_run: bool = False,
) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    suffix = generated_at or _timestamp()
    for proof_type in proof_types:
        payload = load_ops_template(proof_type, generated_at=suffix)
        outputs[proof_type] = payload
        if dry_run:
            continue
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{proof_type}_proof.template.{suffix}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--proof-type",
        choices=["all", *OPS_PROOF_TYPES],
        default="all",
        help="Ops proof template type to generate.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timestamp", help="Stable timestamp/proof suffix for reproducible output.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    proof_types = list(OPS_PROOF_TYPES) if args.proof_type == "all" else [args.proof_type]
    suffix = args.timestamp or _timestamp()
    outputs = write_ops_templates(
        proof_types,
        output_dir=args.output_dir,
        generated_at=suffix,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(json.dumps(outputs, indent=2, sort_keys=True))
    else:
        for proof_type in proof_types:
            print(str(args.output_dir / f"{proof_type}_proof.template.{suffix}.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
