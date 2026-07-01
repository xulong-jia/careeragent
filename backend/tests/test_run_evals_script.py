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
        "agent_workflow": 8,
        "jd_parser": 12,
        "match": 9,
        "project_rewrite": 6,
        "rag_retrieval": 6,
        "resume_parser": 8,
    }
    assert len(cases) == 49


def test_benchmark_loader_reads_large_sample_dataset():
    cases = run_evals._load_benchmark_cases()
    by_module = {}
    for module, _case in cases:
        by_module[module] = by_module.get(module, 0) + 1

    assert by_module == {
        "agent_workflow": 5,
        "jd_parser": 30,
        "match": 10,
        "project_rewrite": 5,
        "rag_answer": 10,
        "rag_retrieval": 20,
        "resume_parser": 20,
    }
    assert len(cases) == 100
    assert len(run_evals._load_benchmark_cases("parser")) == 50
    assert len(run_evals._load_benchmark_cases("rag")) == 30


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

    assert metrics["total_count"] == 12
    assert metrics["by_module"]["jd_parser"]["total"] == 12
    assert "evidence_coverage" in metrics["by_module"]["jd_parser"]["metrics"]
    assert "confidence_present" in metrics["by_module"]["jd_parser"]["metrics"]
    assert run_config["service_level"] is True
    assert run_config["production_quality"] is False
    assert "dataset_kind: service_level" in summary
    assert "production_quality: false" in summary
    assert any(
        "job_service.create_job" in item["actual_output"]["service_calls"]
        for item in actual_outputs
    )
    assert isinstance(failed_cases, list)
    _assert_private_safe(actual_outputs)
    _assert_private_safe(failed_cases)


def test_failed_case_summary_has_bad_case_conversion_fields():
    summary = run_evals._failed_case_summary(
        {
            "case_id": "parser_failure",
            "module": "resume_parser",
            "case_type": "service_level",
            "input_summary": "synthetic resume",
            "expected_output": {"skill": "Python"},
            "actual_output": {"skill": []},
            "error": "Parser missed expected skill.",
        }
    )

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
    }.issubset(summary)
    assert summary["suggested_bad_case_type"] == "missing_skill_extraction"


def test_synthetic_alias_report_is_distinct_from_service_level(tmp_path):
    output_dir = tmp_path / "synthetic-results"

    result_code = run_evals.run("synthetic", None, output_dir)

    assert result_code == 0
    run_config = json.loads((output_dir / "run_config.json").read_text())
    summary = (output_dir / "summary.md").read_text()
    assert run_config["dataset_kind"] == "synthetic_contract"
    assert run_config["service_level"] is False
    assert "dataset_kind: synthetic_contract" in summary


def test_benchmark_runner_writes_ai_quality_metrics(tmp_path):
    output_dir = tmp_path / "benchmark-results"

    result_code = run_evals.run("benchmark", None, output_dir)

    assert result_code == 0
    metrics = json.loads((output_dir / "metrics.json").read_text())
    actual_outputs = json.loads((output_dir / "actual_outputs.json").read_text())
    human_review = json.loads((output_dir / "human_review_summary.json").read_text())
    run_config = json.loads((output_dir / "run_config.json").read_text())
    summary = (output_dir / "summary.md").read_text()

    assert metrics["total_count"] == 100
    assert metrics["failed_count"] == 0
    assert metrics["by_module"]["rag_retrieval"]["metrics"]["recall_at_k"] >= 0.8
    assert metrics["by_module"]["rag_retrieval"]["metrics"]["mrr"] >= 0.5
    assert metrics["by_module"]["rag_answer"]["metrics"]["groundedness"] >= 0.8
    assert metrics["by_module"]["match"]["metrics"]["human_agreement"] == 1.0
    assert metrics["human_review"]["reviewed_count"] == 6
    assert human_review["human_agreement_rate"] >= 0.8
    assert metrics["bad_case_regression_trend"]["candidate_count"] == 0
    assert run_config["dataset_kind"] == "benchmark_foundation"
    assert run_config["large_scale_foundation"] is True
    assert run_config["uses_real_private_data"] is False
    assert "dataset_kind: benchmark_foundation" in summary
    _assert_private_safe(metrics)
    _assert_private_safe(actual_outputs)


def test_service_level_rag_eval_covers_vector_metrics(tmp_path):
    output_dir = tmp_path / "rag-service-level-results"

    result_code = run_evals.run("service_level", "rag", output_dir)

    assert result_code == 0
    metrics = json.loads((output_dir / "metrics.json").read_text())
    actual_outputs = json.loads((output_dir / "actual_outputs.json").read_text())

    assert metrics["total_count"] == 6
    rag_metrics = metrics["by_module"]["rag_retrieval"]["metrics"]
    assert "retrieval_mode_match" in rag_metrics
    assert "average_top_score" in rag_metrics
    assert "vector_index_used" in rag_metrics
    assert any(
        item["actual_output"]["retrieval_debug"]["retrieval_mode"] == "vector"
        for item in actual_outputs
    )
    assert any(
        item["actual_output"]["retrieval_debug"]["retrieval_mode"] == "hybrid"
        for item in actual_outputs
    )
    assert any(
        item["actual_output"]["uncertainty"] == "no_relevant_source"
        for item in actual_outputs
    )


def test_service_level_resume_parser_eval_covers_parser_metrics(tmp_path):
    output_dir = tmp_path / "resume-parser-service-level-results"

    result_code = run_evals.run("service_level", "resume_parser", output_dir)

    assert result_code == 0
    metrics = json.loads((output_dir / "metrics.json").read_text())
    actual_outputs = json.loads((output_dir / "actual_outputs.json").read_text())

    assert metrics["total_count"] == 8
    resume_metrics = metrics["by_module"]["resume_parser"]["metrics"]
    assert "risk_flag_hit_rate" in resume_metrics
    assert "evidence_coverage" in resume_metrics
    assert "confidence_present" in resume_metrics
    assert any(
        item["actual_output"]["parser_metadata"]["foundation_only"] is True
        for item in actual_outputs
    )


def test_service_level_match_eval_covers_trustworthy_metrics(tmp_path):
    output_dir = tmp_path / "match-service-level-results"

    result_code = run_evals.run("service_level", "match", output_dir)

    assert result_code == 0
    metrics = json.loads((output_dir / "metrics.json").read_text())
    match_metrics = metrics["by_module"]["match"]["metrics"]

    assert metrics["total_count"] == 9
    assert "dimension_score_present_rate" in match_metrics
    assert "risk_flag_hit_rate" in match_metrics
    assert "rewrite_priority_hit_rate" in match_metrics
    assert "scoring_method_present" in match_metrics
    assert "confidence_present" in match_metrics


def test_service_level_project_rewrite_eval_covers_guardrail_metrics(tmp_path):
    output_dir = tmp_path / "project-rewrite-service-level-results"

    result_code = run_evals.run("service_level", "project_rewrite", output_dir)

    assert result_code == 0
    metrics = json.loads((output_dir / "metrics.json").read_text())
    rewrite_metrics = metrics["by_module"]["project_rewrite"]["metrics"]

    assert metrics["total_count"] == 6
    assert "before_after_present" in rewrite_metrics
    assert "evidence_required_present" in rewrite_metrics
    assert "forbidden_changes_present" in rewrite_metrics
    assert "risk_level_present" in rewrite_metrics
    assert "fabrication_guard_pass" in rewrite_metrics
