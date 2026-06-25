from app.repositories.resume_repository import (
    archive_resume_version,
    clone_resume_version,
    create_resume_with_initial_version,
    get_resume,
    get_resume_version,
    list_resume_versions,
    list_resumes,
)
from app.models.resume import ResumeVersion
from app.schemas.resumes import StructuredResume


def test_resume_repository_create_list_get(db_session):
    structured_resume = StructuredResume(
        basic_info={"name": None},
        skills={"programming": ["Python"]},
    )

    created = create_resume_with_initial_version(
        db_session,
        filename="repo_resume.md",
        file_type="markdown",
        text_hash="hash",
        parse_status="parsed",
        raw_text="Python project",
        raw_text_preview="Python project",
        structured_resume=structured_resume,
        extraction_status="extracted",
        extraction_method="utf8_md_decode",
        extraction_warnings=[],
        risk_flags=[],
        risk_report={},
    )

    listed = list_resumes(db_session)
    fetched = get_resume(db_session, created.resume_id)

    assert created.resume_id.startswith("resume_")
    assert [item.resume_id for item in listed] == [created.resume_id]
    assert fetched.filename == "repo_resume.md"
    assert fetched.structured_resume.skills["programming"] == ["Python"]


def test_resume_repository_clone_and_archive_version(db_session):
    structured_resume = StructuredResume(
        basic_info={"name": None},
        skills={"programming": ["Python"]},
    )
    created = create_resume_with_initial_version(
        db_session,
        filename="repo_resume.md",
        file_type="markdown",
        text_hash="hash",
        parse_status="parsed",
        raw_text="Python project",
        raw_text_preview="Python project",
        structured_resume=structured_resume,
        extraction_status="extracted",
        extraction_method="utf8_md_decode",
        extraction_warnings=[],
        risk_flags=[],
        risk_report={"passed": True, "flags": []},
    )
    initial = list_resume_versions(db_session, created.resume_id)[0]

    cloned = clone_resume_version(
        db_session,
        initial.resume_version_id,
        version_name="Targeted copy",
        target_role="Backend Engineer",
    )
    archived = archive_resume_version(db_session, initial.resume_version_id)

    assert cloned.resume_id == created.resume_id
    assert cloned.version_number == 2
    assert not hasattr(cloned, "raw_text")
    assert cloned.raw_text_preview == initial.raw_text_preview
    assert cloned.structured_resume == initial.structured_resume
    assert cloned.target_role == "Backend Engineer"
    assert cloned.risk_report == initial.risk_report
    assert archived.status == "archived"
    assert archived.is_archived is True
    fetched_initial = get_resume_version(db_session, initial.resume_version_id)
    assert not hasattr(fetched_initial, "raw_text")
    persisted_initial = db_session.get(ResumeVersion, initial.resume_version_id)
    persisted_clone = db_session.get(ResumeVersion, cloned.resume_version_id)
    assert persisted_initial is not None
    assert persisted_clone is not None
    assert persisted_clone.raw_text == persisted_initial.raw_text
    assert len(list_resume_versions(db_session, created.resume_id)) == 2
