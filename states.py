from __future__ import annotations

from abc import ABC, abstractmethod

from domain import DomainError, DomainInvariantViolation


class TransitionNotAllowed(DomainError):
    def __init__(self, state: str, event: str) -> None:
        self.state = state
        self.event = event
        super().__init__(
            f"Событие '{event}' недопустимо в состоянии '{state}'."
        )


class LendingState(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def allowed_events(self) -> frozenset[str]: ...

    def _deny(self, event: str) -> None:
        raise TransitionNotAllowed(self.name, event)

    def reader_arrived(self, **kwargs) -> "LendingState":
        self._deny("reader_arrived")

    def check_debt(self, **kwargs) -> "LendingState":
        self._deny("check_debt")

    def issue(self, **kwargs) -> "LendingState":
        self._deny("issue")

    def extend(self, **kwargs) -> "LendingState":
        self._deny("extend")

    def return_book(self, **kwargs) -> "LendingState":
        self._deny("return_book")

    def on_reservation_expired(self, **kwargs) -> "LendingState":
        self._deny("on_reservation_expired")

    def on_due_date_expired(self, **kwargs) -> "LendingState":
        self._deny("on_due_date_expired")

    def on_thirty_days_passed(self, **kwargs) -> "LendingState":
        self._deny("on_thirty_days_passed")

    def pay_debt(self, **kwargs) -> "LendingState":
        self._deny("pay_debt")


class Reserved(LendingState):
    @property
    def name(self) -> str:
        return "Забронирована"

    def allowed_events(self) -> frozenset[str]:
        return frozenset({"reader_arrived", "on_reservation_expired"})

    def reader_arrived(self, **kwargs) -> "LendingState":
        return AwaitingReader()

    def on_reservation_expired(self, **kwargs) -> "LendingState":
        return ReservationCancelled()


class AwaitingReader(LendingState):
    @property
    def name(self) -> str:
        return "Ожидает читателя"

    def allowed_events(self) -> frozenset[str]:
        return frozenset({"check_debt", "on_reservation_expired"})

    def check_debt(self, *, has_debt: bool, **kwargs) -> "LendingState":
        if has_debt:
            return Rejected(reason="debt")
        return Checking()

    def on_reservation_expired(self, **kwargs) -> "LendingState":
        return ReservationCancelled()


class Checking(LendingState):
    @property
    def name(self) -> str:
        return "На проверке"

    def allowed_events(self) -> frozenset[str]:
        return frozenset({"issue"})

    def issue(self, **kwargs) -> "LendingState":
        return Issued()


class Issued(LendingState):
    @property
    def name(self) -> str:
        return "Выдана"

    def allowed_events(self) -> frozenset[str]:
        return frozenset({
            "extend", "return_book",
            "on_due_date_expired", "on_thirty_days_passed",
        })

    def extend(
        self, *, has_queue: bool = False,
        already_extended: bool = False, **kwargs,
    ) -> "LendingState":
        if has_queue:
            raise DomainInvariantViolation(
                "На книгу есть очередь — продление невозможно."
            )
        if already_extended:
            raise DomainInvariantViolation(
                "Продление уже использовано."
            )
        return Extended()

    def return_book(
        self, *, has_damage: bool = False,
        is_overdue: bool = False, **kwargs,
    ) -> "LendingState":
        if has_damage or is_overdue:
            return ReturnedWithDebt()
        return Returned()

    def on_due_date_expired(self, **kwargs) -> "LendingState":
        return Overdue()

    def on_thirty_days_passed(self, **kwargs) -> "LendingState":
        return CaseTransferred()


class Extended(LendingState):
    @property
    def name(self) -> str:
        return "Продлена"

    def allowed_events(self) -> frozenset[str]:
        return frozenset({
            "return_book", "on_due_date_expired", "on_thirty_days_passed",
        })

    def return_book(
        self, *, has_damage: bool = False,
        is_overdue: bool = False, **kwargs,
    ) -> "LendingState":
        if has_damage or is_overdue:
            return ReturnedWithDebt()
        return Returned()

    def on_due_date_expired(self, **kwargs) -> "LendingState":
        return Overdue()

    def on_thirty_days_passed(self, **kwargs) -> "LendingState":
        return CaseTransferred()


class Overdue(LendingState):
    @property
    def name(self) -> str:
        return "Просрочена"

    def allowed_events(self) -> frozenset[str]:
        return frozenset({"return_book", "on_thirty_days_passed"})

    def return_book(self, **kwargs) -> "LendingState":
        return ReturnedWithDebt()

    def on_thirty_days_passed(self, **kwargs) -> "LendingState":
        return CaseTransferred()


class ReturnedWithDebt(LendingState):
    @property
    def name(self) -> str:
        return "Возвращена с задолженностью"

    def allowed_events(self) -> frozenset[str]:
        return frozenset({"pay_debt"})

    def pay_debt(self, **kwargs) -> "LendingState":
        return Returned()


class Returned(LendingState):
    @property
    def name(self) -> str:
        return "Возвращена"

    def allowed_events(self) -> frozenset[str]:
        return frozenset()


class Rejected(LendingState):
    def __init__(self, reason: str = "") -> None:
        self._reason = reason

    @property
    def name(self) -> str:
        return "Отказ в выдаче"

    @property
    def reason(self) -> str:
        return self._reason

    def allowed_events(self) -> frozenset[str]:
        return frozenset()


class ReservationCancelled(LendingState):
    @property
    def name(self) -> str:
        return "Бронь снята"

    def allowed_events(self) -> frozenset[str]:
        return frozenset()


class CaseTransferred(LendingState):
    @property
    def name(self) -> str:
        return "Дело передано администрации"

    def allowed_events(self) -> frozenset[str]:
        return frozenset()