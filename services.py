from __future__ import annotations

from datetime import date, timedelta

from aggregates import Loan
from domain import (
    BookId,
    ReaderId,
    LoanPeriod,
    Money,
    DomainError,
)
from repositories import BookRepository, ReaderRepository


class LibraryLendingService:
    def __init__(
        self,
        books: BookRepository,
        readers: ReaderRepository,
    ) -> None:
        self._books = books
        self._readers = readers

    def issue_book(
        self,
        reader_id: ReaderId,
        book_id: BookId,
        issued_on: date,
        loan_period: LoanPeriod,
    ) -> Loan:
        book = self._books.get(book_id)
        reader = self._readers.get(reader_id)

        due_on = issued_on + timedelta(
            days=loan_period.days
        )

        book.checkout_copy()

        try:
            loan = reader.start_loan(
                book_id=book_id,
                issued_on=issued_on,
                due_on=due_on,
            )
        except DomainError:
            book.return_copy()
            raise

        self._books.save(book)
        self._readers.save(reader)

        return loan

    def return_book(
        self,
        reader_id: ReaderId,
        book_id: BookId,
        returned_on: date,
        daily_rate: Money,
    ) -> Money:
        book = self._books.get(book_id)
        reader = self._readers.get(reader_id)

        book.return_copy()

        try:
            fine = reader.close_loan(
                book_id=book_id,
                returned_on=returned_on,
                daily_rate=daily_rate,
            )
        except DomainError:
            book.checkout_copy()
            raise

        self._books.save(book)
        self._readers.save(reader)

        return fine
        