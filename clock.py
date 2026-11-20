from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from domain import DomainInvariantViolation


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Системные часы со сдвигом. Перевод назад запрещён."""

    def __init__(self) -> None:
        self._offset = timedelta(0)

    def now(self) -> datetime:
        return datetime.now() + self._offset

    def set(self, target: datetime) -> None:
        current = self.now()
        if target < current:
            raise DomainInvariantViolation(
                "Перевод часов приложения назад не допускается."
            )
        self._offset += target - current