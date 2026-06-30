from __future__ import annotations

from pathlib import Path
import subprocess


PROMPT_VERSION = "deterministic-v1"
SCHEMA_VERSION = "v1.5"
RETRIEVAL_VERSION = "lexical-v1"
MODEL_VERSION = "none"
EVALUATION_VERSION = "v1.5C"

REPO_ROOT = Path(__file__).resolve().parents[3]


def current_code_version(repo_root: Path = REPO_ROOT) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def version_metadata(*, include_evaluation: bool = False) -> dict[str, str]:
    metadata = {
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "retrieval_version": RETRIEVAL_VERSION,
        "model_version": MODEL_VERSION,
        "code_version": current_code_version(),
    }
    if include_evaluation:
        metadata["evaluation_version"] = EVALUATION_VERSION
    return metadata
