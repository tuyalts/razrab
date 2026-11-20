from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from clock import Clock
from domain import BookId, ReaderId
from events import DomainEvent
from states import LendingState, Reserved, TransitionNotAllowed


@dataclass(frozen=True, slots=True)
class LendingId:
    value: UUID

    @classmethod
    def new(cls) -> "LendingId":
        return cls(uuid4())


class Lending:
    def __init__(
        self,
        lending_id: LendingId,
        book_id: BookId,
        reader_id: ReaderId,
        clock: Clock,
        reserved_until: datetime,
    ) -> None:
        self._id = lending_id
        self._book_id = book_id
        self._reader_id = reader_id
        self._clock = clock
        self._reserved_until = reserved_until
        self._state: LendingState = Reserved()
        self._events: list[DomainEvent] = []
        self._due_on: date | None = None
        self._extension_used = False

    @property
    def id(self) -> LendingId: return self._id
    @property
    def book_id(self) -> BookId: return self._book_id
    @property
    def reader_id(self) -> ReaderId: return self._reader_id
    @property
    def state(self) -> LendingState: return self._state
    @property
    def events(self) -> tuple[DomainEvent, ...]: return tuple(self._events)
    @property
    def due_on(self) -> date | None: return self._due_on
    @property
    def extension_used(self) -> bool: return self._extension_used

    @property
    def allowed_events(self) -> frozenset[str]:
        return self._state.allowed_events()

    def _record(self, name: str, **payload) -> None:
        self._events.append(DomainEvent(
            name=name,
            occurred_at=self._clock.now(),
            payload={"lending_id": str(self._id.value), **payload},
        ))

    def reader_arrived(self) -> None:
        new = self._state.reader_arrived()
        self._state = new
        self._record("ReaderArrived")

    def check_debt(self, *, has_debt: bool) -> None:
        new = self._state.check_debt(has_debt=has_debt)
        self._state = new
        self._record("DebtChecked", has_debt=has_debt)

    def issue(self, *, due_on: date) -> None:
        new = self._state.issue()
        self._due_on = due_on
        self._state = new
        self._record("BookIssued", due_on=due_on.isoformat())

    def extend(
        self, *, has_queue: bool = False, extension_days: int = 7,
    ) -> None:
        new = self._state.extend(
            has_queue=has_queue,
            already_extended=self._extension_used,
        )
        self._extension_used = True
        if self._due_on is not None:
            self._due_on = self._due_on + timedelta(days=extension_days)
        self._state = new
        self._record("LoanExtended")

    def return_book(
        self, *, has_damage: bool = False, is_overdue: bool = False,
    ) -> None:
        new = self._state.return_book(
            has_damage=has_damage, is_overdue=is_overdue,
        )
        self._state = new
        self._record(
            "BookReturned",
            has_damage=has_damage, is_overdue=is_overdue,
        )

    def pay_debt(self) -> None:
        new = self._state.pay_debt()
        self._state = new
        self._record("DebtPaid")

    def on_reservation_expired(self, now: datetime) -> bool:
        if now < self._reserved_until:
            return False
        try:
            new = self._state.on_reservation_expired()
        except TransitionNotAllowed:
            return False
        self._state = new
        self._events.append(DomainEvent(
            name="ReservationExpired",
            occurred_at=now,
            payload={"lending_id": str(self._id.value)},
        ))
        return True

    def on_due_date_expired(self, now: datetime) -> bool:
        if self._due_on is None or now.date() <= self._due_on:
            return False
        try:
            new = self._state.on_due_date_expired()
        except TransitionNotAllowed:
            return False
        self._state = new
        self._events.append(DomainEvent(
            name="DueDateExpired",
            occurred_at=now,
            payload={"lending_id": str(self._id.value)},
        ))
        return True

    def on_thirty_days_passed(self, now: datetime) -> bool:
        if self._due_on is None:
            return False
        deadline = self._due_on + timedelta(days=30)
        if now.date() <= deadline:
            return False
        try:
            new = self._state.on_thirty_days_passed()
        except TransitionNotAllowed:
            return False
        self._state = new
        self._events.append(DomainEvent(
            name="ThirtyDaysPassed",
            occurred_at=now,
            payload={"lending_id": str(self._id.value)},
        ))
        return True