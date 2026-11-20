from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from domain import (
    BookId,
    ReaderId,
    ISBN,
    Money,
    DomainInvariantViolation,
)


@dataclass(frozen=True, slots=True)
class Loan:
    book_id: BookId
    issued_on: date
    due_on: date

    def __post_init__(self) -> None:
        if self.due_on <= self.issued_on:
            raise DomainInvariantViolation(
                "Дата возврата должна быть позже даты выдачи."
            )

    def calculate_fine(
        self,
        returned_on: date,
        daily_rate: Money,
    ) -> Money:
        if returned_on < self.issued_on:
            raise DomainInvariantViolation(
                "Дата возврата не может быть раньше даты выдачи."
            )

        overdue_days = max(0, (returned_on - self.due_on).days)
        fine_amount = daily_rate.amount * overdue_days

        return Money(fine_amount, daily_rate.currency)


class Book:
    def __init__(
        self,
        book_id: BookId,
        title: str,
        isbn: ISBN,
        total_copies: int,
        available_copies: int | None = None,
    ) -> None:
        if not title.strip():
            raise DomainInvariantViolation(
                "Название книги не может быть пустым."
            )

        if total_copies < 1:
            raise DomainInvariantViolation(
                "Общее количество экземпляров должно быть положительным."
            )

        if available_copies is None:
            available_copies = total_copies

        if not 0 <= available_copies <= total_copies:
            raise DomainInvariantViolation(
                "Доступное количество экземпляров указано неверно."
            )

        self._id = book_id
        self._title = title
        self._isbn = isbn
        self._total_copies = total_copies
        self._available_copies = available_copies

    @property
    def id(self) -> BookId:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def isbn(self) -> ISBN:
        return self._isbn

    @property
    def total_copies(self) -> int:
        return self._total_copies

    @property
    def available_copies(self) -> int:
        return self._available_copies

    def checkout_copy(self) -> None:
        if self._available_copies == 0:
            raise DomainInvariantViolation(
                "Нет доступных экземпляров книги."
            )

        self._available_copies -= 1

    def return_copy(self) -> None:
        if self._available_copies >= self._total_copies:
            raise DomainInvariantViolation(
                "Нельзя вернуть книгу, которая не была выдана."
            )

        self._available_copies += 1

    def to_state(self) -> dict[str, object]:
        return {
            "id": str(self._id.value),
            "title": self._title,
            "isbn": self._isbn.value,
            "total_copies": self._total_copies,
            "available_copies": self._available_copies,
        }

    @classmethod
    def from_state(
        cls,
        state: dict[str, object],
    ) -> "Book":
        return cls(
            book_id=BookId(UUID(str(state["id"]))),
            title=str(state["title"]),
            isbn=ISBN(str(state["isbn"])),
            total_copies=int(state["total_copies"]),
            available_copies=int(state["available_copies"]),
        )


class Reader:
    MAX_ACTIVE_LOANS = 5

    def __init__(
        self,
        reader_id: ReaderId,
        name: str,
    ) -> None:
        if not name.strip():
            raise DomainInvariantViolation(
                "Имя читателя не может быть пустым."
            )

        self._id = reader_id
        self._name = name
        self._loans: dict[BookId, Loan] = {}

    @property
    def id(self) -> ReaderId:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def active_loans(self) -> tuple[Loan, ...]:
        return tuple(self._loans.values())

    def start_loan(
        self,
        book_id: BookId,
        issued_on: date,
        due_on: date,
    ) -> Loan:
        if len(self._loans) >= self.MAX_ACTIVE_LOANS:
            raise DomainInvariantViolation(
                "Читатель не может иметь больше пяти активных выдач."
            )

        if book_id in self._loans:
            raise DomainInvariantViolation(
                "Эта книга уже выдана данному читателю."
            )

        loan = Loan(
            book_id=book_id,
            issued_on=issued_on,
            due_on=due_on,
        )

        self._loans[book_id] = loan
        return loan

    def close_loan(
        self,
        book_id: BookId,
        returned_on: date,
        daily_rate: Money,
    ) -> Money:
        loan = self._loans.get(book_id)

        if loan is None:
            raise DomainInvariantViolation(
                "У читателя нет активной выдачи этой книги."
            )

        fine = loan.calculate_fine(
            returned_on=returned_on,
            daily_rate=daily_rate,
        )

        del self._loans[book_id]
        return fine

    def to_state(self) -> dict[str, object]:
        return {
            "id": str(self._id.value),
            "name": self._name,
            "loans": [
                {
                    "book_id": str(loan.book_id.value),
                    "issued_on": loan.issued_on.isoformat(),
                    "due_on": loan.due_on.isoformat(),
                }
                for loan in self._loans.values()
            ],
        }

    @classmethod
    def from_state(
        cls,
        state: dict[str, object],
    ) -> "Reader":
        reader = cls(
            reader_id=ReaderId(UUID(str(state["id"]))),
            name=str(state["name"]),
        )

        loans = state.get("loans", [])

        for loan_state in loans:
            loan_state = dict(loan_state)

            reader.start_loan(
                book_id=BookId(
                    UUID(str(loan_state["book_id"]))
                ),
                issued_on=date.fromisoformat(
                    str(loan_state["issued_on"])
                ),
                due_on=date.fromisoformat(
                    str(loan_state["due_on"])
                ),
            )

        return reader
        