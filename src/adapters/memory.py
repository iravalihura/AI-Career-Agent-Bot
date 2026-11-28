from __future__ import annotations

from src.domain.model import JobApplication


class InMemoryJobApplicationRepository:
    """Адаптер репозиторію у пам'яті."""

    def __init__(self) -> None:
        self._items: dict[str, JobApplication] = {}

    def save(self, application: JobApplication) -> None:
        self._items[application.application_id] = application

    def get_by_id(self, application_id: str) -> JobApplication | None:
        return self._items.get(application_id)