
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from clock import Clock
from domain import BookId, DomainError, ReaderId
from lending import Lending, LendingId
from repositories import BookRepository, ReaderRepository


class GatewayUnresolved(DomainError):
    def __init__(self, gateway_name: str) -> None:
        super().__init__(f"Шлюз '{gateway_name}' не разрешён.")


class LendingRepository(Protocol):
    def get(self, lending_id: LendingId) -> Lending: ...
    def save(self, lending: Lending) -> None: ...
    def all(self) -> list[Lending]: ...


class InMemoryLendingRepository:
    def __init__(self) -> None:
        self._items: dict[LendingId, Lending] = {}

    def get(self, lending_id: LendingId) -> Lending:
        try:
            return self._items[lending_id]
        except KeyError:
            raise DomainError("Выдача не найдена.")

    def save(self, lending: Lending) -> None:
        self._items[lending.id] = lending

    def all(self) -> list[Lending]:
        return list(self._items.values())


class DebtRegistry:
    """Простой реестр долгов читателей."""

    def __init__(self) -> None:
        self._debts: set[UUID] = set()

    def has_debt(self, reader_id: ReaderId) -> bool:
        return reader_id.value in self._debts

    def add(self, reader_id: ReaderId) -> None:
        self._debts.add(reader_id.value)

    def pay(self, reader_id: ReaderId) -> None:
        self._debts.discard(reader_id.value)


class LendingProcess:
    DEFAULT_LOAN_DAYS = 14
    RESERVATION_DAYS = 3

    def __init__(
        self,
        books: BookRepository,
        readers: ReaderRepository,
        lendings: LendingRepository,
        debts: DebtRegistry,
        clock: Clock,
    ) -> None:
        self._books = books
        self._readers = readers
        self._lendings = lendings
        self._debts = debts
        self._clock = clock

    def reserve_book(
        self, book_id: BookId, reader_id: ReaderId,
    ) -> Lending:
        book = self._books.get(book_id)
        reader = self._readers.get(reader_id)

        if book.available_copies <= 0:
            raise DomainError("Нет доступных экземпляров книги.")

        reserved_until = (
            self._clock.now() + timedelta(days=self.RESERVATION_DAYS)
        )
        lending = Lending(
            lending_id=LendingId.new(),
            book_id=book_id,
            reader_id=reader_id,
            clock=self._clock,
            reserved_until=reserved_until,
        )
        book.checkout_copy()
        self._books.save(book)
        self._lendings.save(lending)
        return lending

    def reader_arrived(self, lending_id: LendingId) -> None:
        lending = self._lendings.get(lending_id)
        lending.reader_arrived()
        self._lendings.save(lending)

    def check_debt(self, lending_id: LendingId) -> bool:
        lending = self._lendings.get(lending_id)
        has_debt = self._debts.has_debt(lending.reader_id)
        lending.check_debt(has_debt=has_debt)
        if has_debt:
            book = self._books.get(lending.book_id)
            book.return_copy()
            self._books.save(book)
        self._lendings.save(lending)
        return has_debt

    def issue_book(self, lending_id: LendingId) -> None:
        lending = self._lendings.get(lending_id)
        due_on = (
            self._clock.now().date()
            + timedelta(days=self.DEFAULT_LOAN_DAYS)
        )
        lending.issue(due_on=due_on)
        self._lendings.save(lending)

    def extend_loan(
        self, lending_id: LendingId, has_queue: bool = False,
    ) -> None:
        lending = self._lendings.get(lending_id)
        lending.extend(has_queue=has_queue)
        self._lendings.save(lending)

    def return_book(
        self, lending_id: LendingId, has_damage: bool = False,
    ) -> None:
        lending = self._lendings.get(lending_id)
        is_overdue = (
            lending.due_on is not None
            and self._clock.now().date() > lending.due_on
        )
        lending.return_book(
            has_damage=has_damage, is_overdue=is_overdue,
        )
        book = self._books.get(lending.book_id)
        book.return_copy()
        self._books.save(book)
        if lending.state.name == "Возвращена с задолженностью":
            self._debts.add(lending.reader_id)
        self._lendings.save(lending)

    def pay_debt(self, lending_id: LendingId) -> None:
        lending = self._lendings.get(lending_id)
        lending.pay_debt()
        self._debts.pay(lending.reader_id)
        self._lendings.save(lending)

    def tick(self, now: datetime | None = None) -> dict:
        if now is not None:
            self._clock.set(now)
        current = self._clock.now()
        processed: list[str] = []
        for lending in self._lendings.all():
            prev_name = lending.state.name
            changed = False
            if lending.on_reservation_expired(current):
                if (
                    prev_name == "Забронирована"
                    and lending.state.name == "Бронь снята"
                ):
                    book = self._books.get(lending.book_id)
                    book.return_copy()
                    self._books.save(book)
                changed = True
            if lending.on_due_date_expired(current):
                changed = True
            if lending.on_thirty_days_passed(current):
                changed = True
            if changed:
                self._lendings.save(lending)
                processed.append(str(lending.id.value))
        return {"processed": processed}