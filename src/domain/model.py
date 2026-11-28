from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class DomainError(Exception):
    """Базовий виняток доменного ядра."""


class InvalidCompatibilityScoreError(DomainError):
    """Недопустиме значення об'єкта-значення CompatibilityScore."""


class BusinessInvariantError(DomainError):
    """Порушення бізнес-інваріанта агрегату."""


class InvalidStateTransitionError(DomainError):
    """Заборонений перехід між станами заявки."""


class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    READY_TO_SEND = "READY_TO_SEND"
    SUBMITTED = "SUBMITTED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class CompatibilityScore:
    """Об'єкт-значення: оцінка сумісності профілю та вакансії (0..100)."""

    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise InvalidCompatibilityScoreError("Оцінка сумісності має бути цілим числом.")
        if not (0 <= self.value <= 100):
            raise InvalidCompatibilityScoreError("Оцінка сумісності має бути в межах 0..100.")


@dataclass(frozen=True)
class ApplicationSubmitted:
    """Доменна подія: заявку успішно подано."""

    application_id: str
    candidate_id: str
    vacancy_id: str
    score: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class JobApplication:
    """Корінь агрегату: відгук/заявка кандидата на вакансію."""

    application_id: str
    candidate_id: str
    vacancy_id: str
    score: CompatibilityScore
    min_required_score: CompatibilityScore = field(
        default_factory=lambda: CompatibilityScore(50)
    )
    status: ApplicationStatus = ApplicationStatus.DRAFT
    cover_letter: str | None = None
    _events: list[ApplicationSubmitted] = field(default_factory=list, repr=False)

    def prepare_submission(self, cover_letter: str) -> None:
        """Дозволений перехід DRAFT -> READY_TO_SEND з перевіркою інваріанта сумісності."""
        if self.status != ApplicationStatus.DRAFT:
            raise InvalidStateTransitionError(
                f"Неможливо підготувати заявку зі статусу {self.status.value}."
            )
        if self.score.value < self.min_required_score.value:
            raise BusinessInvariantError(
                f"Оцінка {self.score.value} нижча за мінімальний поріг {self.min_required_score.value}."
            )
        cleaned = cover_letter.strip()
        if not cleaned:
            raise BusinessInvariantError("Супровідний лист не може бути порожнім.")

        self.cover_letter = cleaned
        self.status = ApplicationStatus.READY_TO_SEND

    def submit(self) -> None:
        """Дозволений перехід READY_TO_SEND -> SUBMITTED з генерацією доменної події."""
        if self.status != ApplicationStatus.READY_TO_SEND:
            raise InvalidStateTransitionError(
                f"Неможливо подати заявку зі статусу {self.status.value}."
            )
        if not self.cover_letter or not self.cover_letter.strip():
            raise BusinessInvariantError("Неможливо подати заявку без супровідного листа.")

        self.status = ApplicationStatus.SUBMITTED
        self._events.append(
            ApplicationSubmitted(
                application_id=self.application_id,
                candidate_id=self.candidate_id,
                vacancy_id=self.vacancy_id,
                score=self.score.value,
            )
        )

    def cancel(self) -> None:
        """Дозволений перехід DRAFT/READY_TO_SEND -> CANCELLED."""
        if self.status in (ApplicationStatus.SUBMITTED, ApplicationStatus.CANCELLED):
            raise InvalidStateTransitionError(
                f"Неможливо скасувати заявку зі статусу {self.status.value}."
            )
        self.status = ApplicationStatus.CANCELLED

    def pull_events(self) -> list[ApplicationSubmitted]:
        """Повертає події та очищає список в агрегаті."""
        events = list(self._events)
        self._events.clear()
        return events