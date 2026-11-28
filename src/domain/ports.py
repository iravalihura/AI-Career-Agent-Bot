from __future__ import annotations

from typing import Protocol

from src.domain.model import JobApplication


class JobApplicationRepository(Protocol):
    """Порт репозиторію для збереження та отримання агрегату JobApplication."""

    def save(self, application: JobApplication) -> None:
        """Зберігає агрегат."""
        ...

    def get_by_id(self, application_id: str) -> JobApplication | None:
        """Повертає агрегат за ідентифікатором або None."""
        ...