from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.interview import InterviewAnswer
from app.models.match import MatchReport
from app.models.profile import Profile
from app.models.project import ProjectRewrite
from app.repositories import rag_repository, study_plan_repository
from app.schemas.rag import RagAnswerRunRecord
from app.schemas.study_plans import (
    StudyPlanGenerateRequest,
    StudyPlanRecord,
    StudyPlanStatsResponse,
    StudyTaskStatusUpdateRequest,
)


PREVIEW_CHARS = 180
MANUAL_RESOURCE = {
    "type": "manual_resource_needed",
    "label": "Add a trusted learning resource manually",
}


@dataclass
class TaskCandidate:
    source_gap: str
    title: str
    description: str
    priority: str
    category: str
    acceptance_criteria: list[str]
    evidence_required: list[str]
    source_refs: list[dict[str, str]] = field(default_factory=list)


def generate_study_plan(
    db: Session,
    payload: StudyPlanGenerateRequest,
) -> StudyPlanRecord:
    profile = _get_profile(db, payload.profile_id)
    match_report = _get_match_report(db, payload.match_report_id)
    project_rewrite = _get_project_rewrite(db, payload.project_rewrite_id)
    interview_answers = _get_interview_answers(db, payload.interview_answer_ids)
    rag_answer_runs = _get_rag_answer_runs(db, payload.rag_answer_run_ids)
    target_role = _resolve_target_role(payload.target_role, profile)

    candidates: list[TaskCandidate] = []
    candidates.extend(_tasks_from_match(match_report))
    candidates.extend(_tasks_from_project_rewrite(project_rewrite))
    candidates.extend(_tasks_from_interview_answers(interview_answers))
    candidates.extend(_tasks_from_rag_answer_runs(rag_answer_runs))
    candidates.extend(_tasks_from_request_weakness_tags(payload.weakness_tags))
    candidates.extend(_tasks_from_profile(profile))
    if not candidates:
        candidates.append(_manual_gap_review_task(target_role))

    source_refs = _dedupe_refs(
        [ref for candidate in candidates for ref in candidate.source_refs]
        + _context_refs(profile, match_report, project_rewrite, target_role)
        + _context_refs_from_rag_answer_runs(rag_answer_runs)
    )
    phases = _build_phases(
        candidates,
        available_hours_per_week=payload.available_hours_per_week,
        horizon_weeks=payload.horizon_weeks,
    )

    return study_plan_repository.create_study_plan(
        db,
        match_report_id=match_report.id if match_report else None,
        profile_id=profile.id if profile else None,
        project_rewrite_id=project_rewrite.id if project_rewrite else None,
        target_role=target_role,
        source_refs=source_refs,
        phases=phases,
    )


def list_study_plans(
    db: Session,
    *,
    status: str | None = None,
    target_role: str | None = None,
    profile_id: str | None = None,
    match_report_id: str | None = None,
) -> list[StudyPlanRecord]:
    return study_plan_repository.list_study_plans(
        db,
        status=_normalize_optional_id(status, "status"),
        target_role=_normalize_optional_id(target_role, "target_role"),
        profile_id=_normalize_optional_id(profile_id, "profile_id"),
        match_report_id=_normalize_optional_id(match_report_id, "match_report_id"),
    )


def get_study_plan(db: Session, study_plan_id: str) -> StudyPlanRecord:
    return study_plan_repository.get_study_plan(
        db,
        _normalize_required_id(study_plan_id, "study_plan_id"),
    )


def update_task_status(
    db: Session,
    study_plan_id: str,
    task_id: str,
    payload: StudyTaskStatusUpdateRequest,
) -> StudyPlanRecord:
    normalized_plan_id = _normalize_required_id(study_plan_id, "study_plan_id")
    normalized_task_id = _normalize_required_id(task_id, "task_id")
    plan = study_plan_repository.get_study_plan_model(db, normalized_plan_id)
    if not plan:
        raise AppError(
            code="study_plan_not_found",
            message="Study plan was not found.",
            status_code=404,
            details={"study_plan_id": normalized_plan_id},
        )

    phases = _copy_phases(plan.phases)
    updated = False
    for phase in phases:
        tasks = phase.get("tasks")
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if not isinstance(task, dict):
                continue
            if task.get("task_id") == normalized_task_id:
                task["status"] = payload.status
                updated = True
                break
        if updated:
            break
    if not updated:
        raise AppError(
            code="study_plan_task_not_found",
            message="Study plan task was not found.",
            status_code=404,
            details={
                "study_plan_id": normalized_plan_id,
                "task_id": normalized_task_id,
            },
        )

    return study_plan_repository.update_study_plan_phases(db, plan, phases=phases)


def get_stats(db: Session) -> StudyPlanStatsResponse:
    plans = study_plan_repository.list_study_plan_models(db)
    task_counts = {
        "todo": 0,
        "blocked": 0,
        "done": 0,
        "in_progress": 0,
        "skipped": 0,
    }
    for plan in plans:
        for task in _iter_plan_tasks(plan.phases):
            status = task.get("status")
            if isinstance(status, str) and status in task_counts:
                task_counts[status] += 1

    latest_plan = max(
        plans,
        key=lambda plan: (plan.created_at, plan.id),
        default=None,
    )
    return StudyPlanStatsResponse(
        total_plans=len(plans),
        active_plans=sum(1 for plan in plans if plan.status == "active"),
        completed_plans=sum(1 for plan in plans if plan.status == "completed"),
        archived_plans=sum(1 for plan in plans if plan.status == "archived"),
        pending_tasks=task_counts["todo"],
        blocked_tasks=task_counts["blocked"],
        done_tasks=task_counts["done"],
        in_progress_tasks=task_counts["in_progress"],
        skipped_tasks=task_counts["skipped"],
        latest_plan_id=latest_plan.id if latest_plan else None,
        latest_target_role=latest_plan.target_role if latest_plan else None,
    )


def _get_profile(db: Session, profile_id: str | None) -> Profile | None:
    normalized = _normalize_optional_id(profile_id, "profile_id")
    if normalized is None:
        return None
    profile = db.get(Profile, normalized)
    if not profile:
        raise AppError(
            code="profile_not_found",
            message="Profile was not found.",
            status_code=404,
            details={"profile_id": normalized},
        )
    return profile


def _get_match_report(db: Session, match_report_id: str | None) -> MatchReport | None:
    normalized = _normalize_optional_id(match_report_id, "match_report_id")
    if normalized is None:
        return None
    match_report = db.get(MatchReport, normalized)
    if not match_report:
        raise AppError(
            code="match_report_not_found",
            message="Match report was not found.",
            status_code=404,
            details={"match_report_id": normalized},
        )
    return match_report


def _get_project_rewrite(
    db: Session, project_rewrite_id: str | None
) -> ProjectRewrite | None:
    normalized = _normalize_optional_id(project_rewrite_id, "project_rewrite_id")
    if normalized is None:
        return None
    project_rewrite = db.get(ProjectRewrite, normalized)
    if not project_rewrite:
        raise AppError(
            code="project_rewrite_not_found",
            message="Project rewrite was not found.",
            status_code=404,
            details={"project_rewrite_id": normalized},
        )
    return project_rewrite


def _get_interview_answers(
    db: Session, interview_answer_ids: list[str]
) -> list[InterviewAnswer]:
    answers: list[InterviewAnswer] = []
    for answer_id in _normalize_id_list(interview_answer_ids, "interview_answer_ids"):
        answer = db.get(InterviewAnswer, answer_id)
        if not answer:
            raise AppError(
                code="interview_answer_not_found",
                message="Interview answer was not found.",
                status_code=404,
                details={"interview_answer_id": answer_id},
            )
        answers.append(answer)
    return answers


def _get_rag_answer_runs(
    db: Session, rag_answer_run_ids: list[str]
) -> list[RagAnswerRunRecord]:
    answer_runs: list[RagAnswerRunRecord] = []
    for answer_run_id in _normalize_id_list(rag_answer_run_ids, "rag_answer_run_ids"):
        try:
            answer_runs.append(rag_repository.get_answer_run(db, answer_run_id))
        except AppError as exc:
            if exc.code == "rag_answer_run_not_found":
                raise AppError(
                    code="rag_answer_run_not_found",
                    message="RAG answer run was not found.",
                    status_code=404,
                    details={"rag_answer_run_id": answer_run_id},
                ) from exc
            raise
    return answer_runs


def _resolve_target_role(target_role: str | None, profile: Profile | None) -> str:
    normalized = _clean_text(target_role)
    if normalized:
        return normalized
    if profile:
        for role in list(profile.target_roles or []):
            role_text = _clean_text(role)
            if role_text:
                return role_text
    raise AppError(
        code="study_plan_target_role_required",
        message="Study plan target_role is required when it cannot be inferred.",
        status_code=400,
        details={"field": "target_role"},
    )


def _tasks_from_match(match_report: MatchReport | None) -> list[TaskCandidate]:
    if match_report is None:
        return []
    tasks: list[TaskCandidate] = []
    for index, gap in enumerate(_clean_list(match_report.gaps), start=1):
        priority = "high" if _is_high_priority_gap(gap) else "medium"
        ref = _source_ref(
            "match_report",
            match_report.id,
            "gaps",
            f"Match gap {index}",
            gap,
        )
        tasks.append(
            TaskCandidate(
                source_gap="match_gap",
                title=f"Close match gap: {_short_label(gap)}",
                description=(
                    "Turn this deterministic match gap into a concrete learning "
                    "or evidence task before updating any resume content."
                ),
                priority=priority,
                category="skill",
                acceptance_criteria=[
                    "Write a short note explaining the gap in your own words.",
                    "Create one small deliverable that demonstrates the missing skill or evidence.",
                    "Do not add this claim to a resume until evidence exists.",
                ],
                evidence_required=[
                    "Mini project note, test output, or documented existing evidence."
                ],
                source_refs=[ref],
            )
        )
    for index, priority_text in enumerate(
        _clean_list(match_report.rewrite_priorities), start=1
    ):
        ref = _source_ref(
            "match_report",
            match_report.id,
            "rewrite_priorities",
            f"Rewrite priority {index}",
            priority_text,
        )
        tasks.append(
            TaskCandidate(
                source_gap="match_rewrite_priority",
                title=f"Prepare evidence for rewrite priority {index}",
                description=(
                    "Collect existing facts and decide what can be safely rewritten "
                    "without inventing metrics, companies, users, or production status."
                ),
                priority="medium",
                category="evidence",
                acceptance_criteria=[
                    "List existing facts that support the rewrite priority.",
                    "List unsupported claims that must stay out of the resume.",
                ],
                evidence_required=["Existing project facts and source notes."],
                source_refs=[ref],
            )
        )
    return tasks


def _tasks_from_project_rewrite(
    project_rewrite: ProjectRewrite | None,
) -> list[TaskCandidate]:
    if project_rewrite is None:
        return []
    tasks: list[TaskCandidate] = []
    for index, item in enumerate(list(project_rewrite.missing_points or []), start=1):
        if not isinstance(item, dict):
            continue
        requirement = _clean_text(item.get("requirement")) or "required skill"
        priority = "high" if item.get("priority") == "high" else "medium"
        ref = _source_ref(
            "project_rewrite",
            project_rewrite.id,
            "missing_points",
            f"Missing point {index}",
            requirement,
        )
        tasks.append(
            TaskCandidate(
                source_gap="missing_required_skill",
                title=f"Build a mini deliverable for {requirement}",
                description=(
                    "Create a small, verifiable learning deliverable for this missing "
                    "project/JD requirement instead of claiming experience you do not have."
                ),
                priority=priority,
                category="skill",
                acceptance_criteria=[
                    "Deliverable runs locally or is documented with clear steps.",
                    "Notes distinguish learned practice from professional project experience.",
                ],
                evidence_required=["README note, command output, or short demo artifact."],
                source_refs=[ref],
            )
        )
    for index, item in enumerate(
        list(project_rewrite.evidence_required or []), start=1
    ):
        if not isinstance(item, dict):
            continue
        evidence_type = _clean_text(item.get("type")) or "missing_evidence"
        reason = _clean_text(item.get("reason")) or evidence_type
        ref = _source_ref(
            "project_rewrite",
            project_rewrite.id,
            "evidence_required",
            f"Evidence required {index}",
            reason,
        )
        tasks.append(
            TaskCandidate(
                source_gap=evidence_type,
                title=f"Collect project evidence: {evidence_type}",
                description=(
                    "Document existing proof and remove unsupported claims before "
                    "using this project in interview or resume material."
                ),
                priority="high",
                category="evidence",
                acceptance_criteria=[
                    "Evidence note states what is proven and what is not proven.",
                    "Unsupported metrics or scale claims are explicitly excluded.",
                ],
                evidence_required=["Existing code, test output, screenshots, or notes."],
                source_refs=[ref],
            )
        )
    return tasks


def _tasks_from_interview_answers(
    interview_answers: list[InterviewAnswer],
) -> list[TaskCandidate]:
    tasks: list[TaskCandidate] = []
    for answer in interview_answers:
        weakness_tags = _clean_list(answer.weakness_tags)
        low_score_dimensions = _low_score_dimensions(dict(answer.scores or {}))
        for tag in [*weakness_tags, *low_score_dimensions]:
            tasks.append(_task_for_weakness_tag(tag, answer.id, "interview_answer"))
    return tasks


def _tasks_from_rag_answer_runs(
    answer_runs: list[RagAnswerRunRecord],
) -> list[TaskCandidate]:
    tasks: list[TaskCandidate] = []
    for answer_run in answer_runs:
        if not answer_run.grounded:
            continue
        refs = _source_refs_from_rag_answer_run(answer_run)
        if not refs:
            continue
        summary = _clean_list(answer_run.evidence_summary)
        preview = summary[0] if summary else answer_run.question
        tasks.append(
            TaskCandidate(
                source_gap="rag_grounded_evidence",
                title=f"Review RAG evidence: {_short_label(answer_run.question)}",
                description=(
                    "Use this grounded RAG answer run as a reference for learning "
                    "or evidence review. Do not treat it as personal project experience."
                ),
                priority="low",
                category="evidence",
                acceptance_criteria=[
                    "Summarize what the RAG source supports and what it does not support.",
                    "Do not add any claim to resume, project, or interview answers unless separately verified.",
                ],
                evidence_required=["RAG answer run source refs and a manual verification note."],
                source_refs=[
                    _source_ref(
                        "rag_answer_run",
                        answer_run.answer_run_id,
                        "evidence_summary",
                        "Grounded RAG answer",
                        preview,
                    ),
                    *refs,
                ],
            )
        )
    return tasks


def _tasks_from_request_weakness_tags(weakness_tags: list[str]) -> list[TaskCandidate]:
    return [
        _task_for_weakness_tag(tag, "generate_request", "request")
        for tag in _clean_list(weakness_tags)
    ]


def _tasks_from_profile(profile: Profile | None) -> list[TaskCandidate]:
    if profile is None:
        return []
    tasks: list[TaskCandidate] = []
    for category, values in dict(profile.skill_map or {}).items():
        skills = _clean_list(values if isinstance(values, list) else [values])
        for skill in skills:
            ref = _source_ref(
                "profile",
                profile.id,
                f"skill_map.{category}",
                "Profile skill map",
                skill,
            )
            tasks.append(
                TaskCandidate(
                    source_gap="profile_skill_deepening",
                    title=f"Deepen practical proof for {skill}",
                    description=(
                        "Turn this profile skill into a concrete practice artifact "
                        "with evidence and limits."
                    ),
                    priority="low",
                    category="skill",
                    acceptance_criteria=[
                        "Produce a short artifact or note showing practical usage.",
                        "Record limitations and avoid overstating experience.",
                    ],
                    evidence_required=["Practice note or existing project evidence."],
                    source_refs=[ref],
                )
            )
    return tasks[:3]


def _task_for_weakness_tag(
    tag: str,
    source_id: str,
    source_type: str,
) -> TaskCandidate:
    ref = _source_ref(
        source_type,
        source_id,
        "weakness_tags",
        "Interview weakness tag",
        tag,
    )
    mapping = {
        "missing_evidence": (
            "Collect evidence for interview claims",
            "Prepare proof for claims before reusing them in answers.",
            "evidence",
            "high",
            ["Answer cites only existing facts or clearly labels uncertainty."],
            ["Existing project note, test output, or source reference."],
        ),
        "unsupported_metric": (
            "Audit unsupported metrics",
            "Remove or qualify metrics that are not backed by existing evidence.",
            "evidence",
            "high",
            ["Unsupported metrics are removed or backed by documented evidence."],
            ["Metric source, calculation note, or decision to omit the metric."],
        ),
        "shallow_technical_depth": (
            "Prepare a technical deep dive",
            "Expand implementation details, tradeoffs, and boundaries using existing facts.",
            "skill",
            "medium",
            ["Technical explanation includes design choice, tradeoff, and limitation."],
            ["Architecture note or code walkthrough outline."],
        ),
        "weak_business_understanding": (
            "Map technical work to business scenario",
            "Explain how existing work connects to the JD scenario without inventing impact.",
            "skill",
            "medium",
            ["Business explanation names the user/workflow/risk served by the work."],
            ["JD requirement note and matching project fact."],
        ),
        "weak_structure": (
            "Rewrite answer with STAR/PAR structure",
            "Reorganize the answer into context, action, evidence, and result.",
            "interview",
            "medium",
            ["Answer draft has context, action, evidence, result, and limitation."],
            ["Structured answer draft."],
        ),
        "unclear_expression": (
            "Clarify interview expression",
            "Shorten generic statements and make the personal action explicit.",
            "interview",
            "medium",
            ["Answer draft uses concise sentences and clear personal actions."],
            ["Rewritten answer draft."],
        ),
        "overclaim_risk": (
            "Run claim audit",
            "Delete claims not supported by source refs or existing material.",
            "evidence",
            "high",
            ["Every strong claim is either supported or removed."],
            ["Claim audit checklist."],
        ),
    }
    title, description, category, priority, criteria, evidence = mapping.get(
        tag,
        (
            f"Review weakness: {tag}",
            "Convert this weakness into one specific practice task.",
            "interview",
            "low",
            ["Weakness is translated into a concrete next action."],
            ["Short action note."],
        ),
    )
    return TaskCandidate(
        source_gap=tag,
        title=title,
        description=description,
        priority=priority,
        category=category,
        acceptance_criteria=criteria,
        evidence_required=evidence,
        source_refs=[ref],
    )


def _manual_gap_review_task(target_role: str) -> TaskCandidate:
    ref = _source_ref(
        "request",
        "generate_request",
        "target_role",
        "Target role",
        target_role,
    )
    return TaskCandidate(
        source_gap="manual_gap_review",
        title=f"Manually review learning gaps for {target_role}",
        description=(
            "No structured gaps were provided, so start by writing a short gap review "
            "from the target role and existing profile context."
        ),
        priority="medium",
        category="skill",
        acceptance_criteria=[
            "List three role requirements to validate against your current evidence.",
            "Mark each requirement as proven, needs practice, or needs evidence.",
        ],
        evidence_required=["Manual gap review note."],
        source_refs=[ref],
    )


def _build_phases(
    candidates: list[TaskCandidate],
    *,
    available_hours_per_week: int,
    horizon_weeks: int,
) -> list[dict[str, object]]:
    categories = [
        ("evidence", "Evidence and risk control", "Make claims safe and verifiable."),
        ("skill", "Skill and project practice", "Close role gaps with concrete artifacts."),
        ("interview", "Interview answer practice", "Convert weak answer signals into structured practice."),
    ]
    phases: list[dict[str, object]] = []
    task_counter = 1
    for phase_index, (category, phase_name, goal) in enumerate(categories, start=1):
        tasks = [candidate for candidate in candidates if candidate.category == category]
        if not tasks:
            continue
        phase_tasks: list[dict[str, object]] = []
        for candidate in sorted(tasks, key=_priority_sort_key):
            phase_tasks.append(
                {
                    "task_id": f"task_{task_counter:04d}",
                    "title": candidate.title,
                    "description": candidate.description,
                    "source_gap": candidate.source_gap,
                    "priority": candidate.priority,
                    "status": "todo",
                    "due_hint": _due_hint(task_counter, horizon_weeks),
                    "acceptance_criteria": candidate.acceptance_criteria,
                    "evidence_required": candidate.evidence_required,
                    "source_refs": candidate.source_refs,
                }
            )
            task_counter += 1
        phases.append(
            {
                "phase_id": f"phase_{phase_index:04d}",
                "phase": phase_name,
                "goal": f"{goal} Planned at {available_hours_per_week}h/week for {horizon_weeks} weeks.",
                "tasks": phase_tasks,
                "resources": [dict(MANUAL_RESOURCE)],
                "deliverables": _phase_deliverables(category),
                "acceptance_criteria": [
                    "All tasks in this phase have an explicit deliverable.",
                    "No resume, project, or interview answer is automatically modified.",
                ],
            }
        )
    return phases


def _context_refs(
    profile: Profile | None,
    match_report: MatchReport | None,
    project_rewrite: ProjectRewrite | None,
    target_role: str,
) -> list[dict[str, str]]:
    refs = [
        _source_ref("request", "generate_request", "target_role", "Target role", target_role)
    ]
    if profile:
        refs.append(
            _source_ref(
                "profile",
                profile.id,
                "target_roles",
                "Profile target roles",
                ", ".join(_clean_list(profile.target_roles)),
            )
        )
    if match_report:
        refs.append(
            _source_ref(
                "match_report",
                match_report.id,
                "dimension_scores",
                "Match dimension scores",
                ", ".join(sorted((match_report.dimension_scores or {}).keys())),
            )
        )
    if project_rewrite:
        refs.append(
            _source_ref(
                "project_rewrite",
                project_rewrite.id,
                "rewrite_strategy",
                "Project rewrite",
                project_rewrite.rewrite_strategy,
            )
        )
    return refs


def _context_refs_from_rag_answer_runs(
    answer_runs: list[RagAnswerRunRecord],
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for answer_run in answer_runs:
        if answer_run.grounded:
            refs.append(
                _source_ref(
                    "rag_answer_run",
                    answer_run.answer_run_id,
                    "question",
                    "Grounded RAG answer run",
                    answer_run.question,
                )
            )
        else:
            refs.append(
                _source_ref(
                    "rag_answer_run",
                    answer_run.answer_run_id,
                    "uncertainty",
                    "Ungrounded RAG answer run",
                    answer_run.uncertainty,
                )
            )
    return refs


def _source_refs_from_rag_answer_run(
    answer_run: RagAnswerRunRecord,
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for index, source_ref in enumerate(answer_run.source_refs[:3], start=1):
        refs.append(
            _source_ref(
                source_ref.source_type,
                source_ref.source_id,
                source_ref.field,
                source_ref.label or f"RAG source ref {index}",
                source_ref.preview,
            )
        )
    if refs:
        return refs
    for index, citation in enumerate(answer_run.citations[:3], start=1):
        refs.append(
            _source_ref(
                "rag_chunk",
                citation.chunk_id,
                "snippet",
                citation.label or f"RAG citation {index}",
                citation.snippet,
            )
        )
    return refs


def _source_ref(
    source_type: str,
    source_id: str,
    field: str,
    label: str,
    preview: object,
) -> dict[str, str]:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "field": field,
        "label": label,
        "preview": _preview(str(preview)),
    }


def _dedupe_refs(refs: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[dict[str, str]] = []
    for ref in refs:
        key = (
            ref["source_type"],
            ref["source_id"],
            ref["field"],
            ref["preview"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def _low_score_dimensions(scores: dict[str, object]) -> list[str]:
    tags: list[str] = []
    mapping = {
        "structure": "weak_structure",
        "technical_depth": "shallow_technical_depth",
        "business_understanding": "weak_business_understanding",
        "evidence": "missing_evidence",
        "clarity": "unclear_expression",
        "risk_control": "overclaim_risk",
    }
    for dimension, tag in mapping.items():
        value = scores.get(dimension)
        if isinstance(value, int | float) and value <= 2:
            tags.append(tag)
    return tags


def _priority_sort_key(candidate: TaskCandidate) -> tuple[int, str]:
    order = {"high": 0, "medium": 1, "low": 2}
    return (order.get(candidate.priority, 3), candidate.title)


def _phase_deliverables(category: str) -> list[str]:
    if category == "evidence":
        return ["Evidence checklist", "Claim audit notes"]
    if category == "skill":
        return ["Mini deliverable", "Learning notes"]
    return ["Structured answer draft", "Practice feedback notes"]


def _due_hint(task_index: int, horizon_weeks: int) -> str:
    week = min(horizon_weeks, max(1, task_index))
    return f"week_{week}"


def _normalize_optional_id(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise AppError(
            code="validation_error",
            message=f"{field_name} must not be empty.",
            status_code=400,
            details={"field": field_name},
        )
    return normalized


def _normalize_required_id(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            code="validation_error",
            message=f"{field_name} must not be empty.",
            status_code=400,
            details={"field": field_name},
        )
    return normalized


def _normalize_id_list(values: list[str], field_name: str) -> list[str]:
    normalized: list[str] = []
    for value in values:
        item = value.strip()
        if not item:
            raise AppError(
                code="validation_error",
                message=f"{field_name} must not contain empty strings.",
                status_code=400,
                details={"field": field_name},
            )
        normalized.append(item)
    return normalized


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        text = _clean_text(item)
        if text:
            cleaned.append(text)
    return cleaned


def _preview(value: str) -> str:
    return _clean_text(value)[:PREVIEW_CHARS]


def _short_label(value: str) -> str:
    preview = _preview(value)
    return preview if len(preview) <= 72 else f"{preview[:69]}..."


def _is_high_priority_gap(value: str) -> bool:
    lower = value.lower()
    return any(term in lower for term in ("missing", "required", "risk", "evidence"))


def _copy_phases(value: object) -> list[dict[str, object]]:
    phases: list[dict[str, object]] = []
    if not isinstance(value, list):
        return phases
    for phase in value:
        if not isinstance(phase, dict):
            continue
        copied_phase = dict(phase)
        copied_tasks: list[dict[str, object]] = []
        for task in list(copied_phase.get("tasks") or []):
            if isinstance(task, dict):
                copied_tasks.append(dict(task))
        copied_phase["tasks"] = copied_tasks
        phases.append(copied_phase)
    return phases


def _iter_plan_tasks(phases: object) -> Iterable[dict[str, object]]:
    if not isinstance(phases, list):
        return
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        tasks = phase.get("tasks")
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if isinstance(task, dict):
                yield task
