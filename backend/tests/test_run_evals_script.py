import json
import subprocess
import sys

from scripts import run_evals


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
    assert (output_dir / "actual_outputs.json").exists()
    assert (output_dir / "run_config.json").exists()
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


def test_service_level_loader_reads_dataset_cases():
    cases = run_evals._load_service_level_cases()
    by_module = {}
    for module, _case in cases:
        by_module[module] = by_module.get(module, 0) + 1

    assert by_module == {
        "agent_workflow": 3,
        "jd_parser": 8,
        "match": 5,
        "rag_retrieval": 5,
        "resume_parser": 5,
    }
    assert len(cases) == 26


def test_eval_metrics_aggregate_module_metrics():
    metrics = run_evals._build_metrics(
        [
            {
                "case_id": "a",
                "module": "jd_parser",
                "passed": True,
                "metrics": {"case_pass": True, "hit_rate": 1.0},
            },
            {
                "case_id": "b",
                "module": "jd_parser",
                "passed": False,
                "metrics": {"case_pass": False, "hit_rate": 0.5},
            },
        ],
        run_config={"dataset_name": "unit"},
    )

    assert metrics["total_cases"] == 2
    assert metrics["passed_cases"] == 1
    assert metrics["failed_cases"] == 1
    assert metrics["by_module"]["jd_parser"]["pass_rate"] == 0.5
    assert metrics["by_module"]["jd_parser"]["metrics"]["hit_rate"] == 0.75
    assert metrics["by_module"]["jd_parser"]["metrics"]["case_pass"] == 0.5


def test_service_level_runner_writes_outputs_and_calls_real_service(tmp_path):
    output_dir = tmp_path / "service-level-results"

    result_code = run_evals.run("service_level", "jd_parser", output_dir)

    assert result_code == 0
    metrics = json.loads((output_dir / "metrics.json").read_text())
    failed_cases = json.loads((output_dir / "failed_cases.json").read_text())
    actual_outputs = json.loads((output_dir / "actual_outputs.json").read_text())
    run_config = json.loads((output_dir / "run_config.json").read_text())
    summary = (output_dir / "summary.md").read_text()

    assert metrics["total_count"] == 8
    assert metrics["by_module"]["jd_parser"]["total"] == 8
    assert run_config["service_level"] is True
    assert run_config["production_quality"] is False
    assert "dataset_kind: service_level" in summary
    assert "production_quality: false" in summary
    assert any(
        "job_service.create_job" in item["actual_output"]["service_calls"]
        for item in actual_outputs
    )
    assert failed_cases
    assert {
        "case_id",
        "module",
        "case_type",
        "failure_type",
        "input_summary",
        "expected_summary",
        "actual_summary",
        "failure_reason",
        "suggested_bad_case_type",
    }.issubset(failed_cases[0])
    _assert_private_safe(actual_outputs)
    _assert_private_safe(failed_cases)


def test_synthetic_alias_report_is_distinct_from_service_level(tmp_path):
    output_dir = tmp_path / "synthetic-results"

    result_code = run_evals.run("synthetic", None, output_dir)

    assert result_code == 0
    run_config = json.loads((output_dir / "run_config.json").read_text())
    summary = (output_dir / "summary.md").read_text()
    assert run_config["dataset_kind"] == "synthetic_contract"
    assert run_config["service_level"] is False
    assert "dataset_kind: synthetic_contract" in summary
