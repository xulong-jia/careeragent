from app.schemas.jobs import JobRecord
from app.schemas.matches import MatchReport
from app.schemas.resumes import ResumeRecord


class MockStore:
    def __init__(self) -> None:
        self.resumes: dict[str, ResumeRecord] = {}
        self.jobs: dict[str, JobRecord] = {}
        self.matches: dict[str, MatchReport] = {}

    def next_id(self, prefix: str, existing_count: int) -> str:
        return f"{prefix}_{existing_count + 1:04d}"


store = MockStore()
