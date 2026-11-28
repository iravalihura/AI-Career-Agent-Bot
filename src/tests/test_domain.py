import pytest

from src.adapters.memory import InMemoryJobApplicationRepository
from src.domain.model import (
    ApplicationStatus,
    ApplicationSubmitted,
    BusinessInvariantError,
    CompatibilityScore,
    InvalidCompatibilityScoreError,
    InvalidStateTransitionError,
    JobApplication,
)


def test_create_save_and_get_aggregate() -> None:
    repo = InMemoryJobApplicationRepository()
    app = JobApplication(
        application_id="app-1",
        candidate_id="cand-1",
        vacancy_id="vac-1",
        score=CompatibilityScore(82),
    )

    repo.save(app)
    fetched = repo.get_by_id("app-1")

    assert fetched is not None
    assert fetched.application_id == "app-1"
    assert fetched.score == CompatibilityScore(82)
    assert fetched.status == ApplicationStatus.DRAFT


def test_invalid_score_value() -> None:
    with pytest.raises(InvalidCompatibilityScoreError):
        CompatibilityScore(150)

    with pytest.raises(InvalidCompatibilityScoreError):
        CompatibilityScore(-5)


def test_business_invariant_violation() -> None:
    app = JobApplication(
        application_id="app-2",
        candidate_id="cand-1",
        vacancy_id="vac-2",
        score=CompatibilityScore(35),
        min_required_score=CompatibilityScore(50),
    )

    with pytest.raises(BusinessInvariantError):
        app.prepare_submission("Супровідний лист")


def test_forbidden_state_transition() -> None:
    app = JobApplication(
        application_id="app-3",
        candidate_id="cand-1",
        vacancy_id="vac-3",
        score=CompatibilityScore(75),
    )

    with pytest.raises(InvalidStateTransitionError):
        app.submit()


def test_successful_submission_emits_domain_event() -> None:
    repo = InMemoryJobApplicationRepository()
    app = JobApplication(
        application_id="app-4",
        candidate_id="cand-1",
        vacancy_id="vac-4",
        score=CompatibilityScore(91),
    )

    app.prepare_submission("Маю досвід з розробки та проєктування.")
    app.submit()
    repo.save(app)

    events = app.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], ApplicationSubmitted)
    assert events[0].application_id == "app-4"
    assert events[0].score == 91
    assert repo.get_by_id("app-4").status == ApplicationStatus.SUBMITTED