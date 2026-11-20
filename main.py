from datetime import date
from decimal import Decimal

from aggregates import Book, Reader
from domain import (
    BookId,
    ReaderId,
    ISBN,
    LoanPeriod,
    Money,
    InvalidValueObject,
    DomainError,
)
from factories import AggregateFactory
from repositories import (
    InMemoryBookRepository,
    InMemoryReaderRepository,
)
from services import LibraryLendingService


def main() -> None:
    books = InMemoryBookRepository()
    readers = InMemoryReaderRepository()

    book = Book(
        book_id=BookId.new(),
        title="1984",
        isbn=ISBN("9780451524935"),
        total_copies=1,
    )

    reader = Reader(
        reader_id=ReaderId.new(),
        name="Селихова П. С.",
    )

    books.save(book)
    readers.save(reader)

    service = LibraryLendingService(
        books=books,
        readers=readers,
    )

    issued_on = date(2026, 10, 1)

    loan = service.issue_book(
        reader_id=reader.id,
        book_id=book.id,
        issued_on=issued_on,
        loan_period=LoanPeriod(7),
    )

    print("Книга выдана.")
    print(f"Дата возврата: {loan.due_on}")
    print(
        f"Доступных экземпляров: "
        f"{book.available_copies}"
    )

    try:
        service.issue_book(
            reader_id=reader.id,
            book_id=book.id,
            issued_on=issued_on,
            loan_period=LoanPeriod(7),
        )
    except DomainError as error:
        print(f"Ошибка повторной выдачи: {error}")

    fine = service.return_book(
        reader_id=reader.id,
        book_id=book.id,
        returned_on=date(2026, 10, 12),
        daily_rate=Money(Decimal("50")),
    )

    print("Книга возвращена.")
    print(f"Штраф: {fine.amount} {fine.currency}")
    print(
        f"Доступных экземпляров: "
        f"{book.available_copies}"
    )

    book_state = book.to_state()
    reader_state = reader.to_state()

    restored_book = AggregateFactory.restore_book(
        book_state
    )
    restored_reader = AggregateFactory.restore_reader(
        reader_state
    )

    print("Агрегаты восстановлены.")
    print(
        f"Восстановленная книга: "
        f"{restored_book.title}"
    )
    print(
        f"Активных выдач читателя: "
        f"{len(restored_reader.active_loans)}"
    )

    try:
        ISBN("123")
    except InvalidValueObject as error:
        print(f"Ошибка проверки ISBN: {error}")


if __name__ == "__main__":
    main()
    