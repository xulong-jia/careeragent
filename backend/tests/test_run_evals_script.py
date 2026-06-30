import json
import subprocess
import sys


PRIVATE_TEXT_KEYS = {
    "raw_text",
    "jd_raw_text",
    "chunk_text",
    "full_text",
    "resume_text",
    "job_text",
}


def _assert_private_safe(value):
    if isinstance(value, dict):
        assert PRIVATE_TEXT_KEYS.isdisjoint(value.keys())
        for child in value.values():
            _assert_private_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_private_safe(child)


def test_run_evals_smoke_writes_summary_metrics_and_failed_cases(tmp_path):
    output_dir = tmp_path / "smoke-results"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_evals.py",
            "--dataset",
            "smoke",
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    metrics = json.loads((output_dir / "metrics.json").read_text())
    failed_cases = json.loads((output_dir / "failed_cases.json").read_text())
    summary = (output_dir / "summary.md").read_text()
    assert metrics["total_count"] == 7
    assert metrics["passed_count"] == 7
    assert metrics["failed_count"] == 0
    assert metrics["failed_case_ids"] == []
    assert failed_cases == []
    assert "llm_judge: false" in summary
    _assert_private_safe(metrics)
    _assert_private_safe(failed_cases)


def test_run_evals_regression_empty_dataset_is_successful(tmp_path):
    output_dir = tmp_path / "regression-results"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_evals.py",
            "--dataset",
            "regression",
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    metrics = json.loads((output_dir / "metrics.json").read_text())
    assert metrics["total_count"] == 0
    assert metrics["failed_count"] == 0
    assert metrics["pass_rate"] == 0.0
