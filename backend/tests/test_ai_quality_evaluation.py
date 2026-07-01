from app.evaluation import ai_quality


def test_human_review_calibration_and_score_stability():
    records = ai_quality.parse_human_review_records(
        [
            {
                "case_id": "case_a",
                "module": "match",
                "system_score": 82,
                "human_score": 79,
                "human_label": "accept",
                "reviewer_confidence": 0.9,
                "accepted_strengths": ["skills"],
                "missed_gaps": [],
                "overclaim_flags": [],
            },
            {
                "case_id": "case_b",
                "module": "match",
                "system_score": 65,
                "human_score": 54,
                "human_label": "major_gap",
                "reviewer_confidence": 0.8,
                "accepted_strengths": [],
                "missed_gaps": ["evidence"],
                "overclaim_flags": ["scale"],
            },
        ]
    )

    calibration = ai_quality.compute_match_calibration(records)
    stability = ai_quality.score_stability(
        [{"case_id": "case_a", "score": 82}, {"case_id": "case_b", "score": 65}],
        [{"case_id": "case_a", "score": 80}, {"case_id": "case_b", "score": 71}],
    )

    assert calibration["reviewed_count"] == 2
    assert calibration["disagreement_rate"] == 0.5
    assert calibration["dimension_disagreement"]["missed_gap_count"] == 1
    assert stability["max_score_delta"] == 6
    assert stability["changed_case_ids"] == ["case_b"]


def test_failed_case_to_bad_case_regression_trend_is_privacy_safe():
    failed_cases = [
        {
            "case_id": "rag_failure",
            "module": "rag_retrieval",
            "failure_type": "irrelevant_rag_source",
            "failure_reason": "Expected chunk was not retrieved.",
        }
    ]

    trend = ai_quality.bad_case_regression_trend(failed_cases, reopened_case_count=1)

    assert trend["candidate_count"] == 1
    assert trend["regression_pass_rate"] == 0.5
    assert trend["bad_case_candidates"][0]["source_type"] == "evaluation_case"
    assert trend["bad_case_candidates"][0]["privacy_safe"] is True
