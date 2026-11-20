from datetime import timedelta
from aggregates import Book, Reader
from clock import SystemClock
from domain import BookId, ReaderId, ISBN
from process import (
    DebtRegistry,
    InMemoryLendingRepository,
    LendingProcess,
)
from repositories import (
    InMemoryBookRepository,
    InMemoryReaderRepository,
)
from states import TransitionNotAllowed


def main() -> None:
    books = InMemoryBookRepository()
    readers = InMemoryReaderRepository()
    lendings = InMemoryLendingRepository()
    debts = DebtRegistry()
    clock = SystemClock()

    book = Book(
        book_id=BookId.new(),
        title="1984",
        isbn=ISBN("9780451524935"),
        total_copies=1,
    )
    reader = Reader(reader_id=ReaderId.new(), name="Селихова П. С.")
    books.save(book)
    readers.save(reader)

    process = LendingProcess(
        books=books,
        readers=readers,
        lendings=lendings,
        debts=debts,
        clock=clock,
    )

    print("--- Сценарий 1: Успешная выдача ---")
    lending = process.reserve_book(book.id, reader.id)
    print(f"Забронировали. Текущее состояние: {lending.state.name}")

    process.reader_arrived(lending.id)
    print(f"Читатель пришел. Состояние: {lending.state.name}")

    process.check_debt(lending.id)
    print(f"Проверили долги. Состояние: {lending.state.name}")

    process.issue_book(lending.id)
    print(f"Выдали книгу. Состояние: {lending.state.name}")

    process.extend_loan(lending.id)
    print(f"Продлили книгу. Состояние: {lending.state.name}")

    process.return_book(lending.id)
    print(f"Вернули книгу. Состояние: {lending.state.name}")

    print("\n--- Сценарий 2: Недопустимое действие ---")
    try:
        process.return_book(lending.id)  # Пытаемся вернуть уже возвращенную
    except TransitionNotAllowed as e:
        print(f"Ожидаемая ошибка: {e}")

    print("\n--- Сценарий 3: Срабатывание таймера (Просрочка) ---")
    lending2 = process.reserve_book(book.id, reader.id)
    process.reader_arrived(lending2.id)
    process.check_debt(lending2.id)
    process.issue_book(lending2.id)
    
    # Сдвигаем время на 20 дней вперед (книга выдана на 14)
    future_time = clock.now() + timedelta(days=20)
    print(f"Переводим часы на: {future_time.date()}")
    
    result = process.tick(now=future_time)
    print(f"Сработали таймеры для выдач: {result['processed']}")
    print(f"Новое состояние выдачи: {lending2.state.name}")


if __name__ == "__main__":
    main()