from app.repositories.resume_repository import (
    create_resume_with_initial_version,
    get_resume,
    list_resumes,
)
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
        raw_text="Python project",
        raw_text_preview="Python project",
        structured_resume=structured_resume,
        extraction_status="extracted",
        extraction_method="utf8_md_decode",
        extraction_warnings=[],
        risk_flags=[],
    )

    listed = list_resumes(db_session)
    fetched = get_resume(db_session, created.resume_id)

    assert created.resume_id.startswith("resume_")
    assert [item.resume_id for item in listed] == [created.resume_id]
    assert fetched.filename == "repo_resume.md"
    assert fetched.structured_resume.skills["programming"] == ["Python"]
