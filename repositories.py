from __future__ import annotations

from typing import Protocol

from aggregates import Book, Reader
from domain import BookId, ReaderId, DomainError


class BookRepository(Protocol):
    def get(self, book_id: BookId) -> Book:
        ...

    def save(self, book: Book) -> None:
        ...


class ReaderRepository(Protocol):
    def get(self, reader_id: ReaderId) -> Reader:
        ...

    def save(self, reader: Reader) -> None:
        ...


class InMemoryBookRepository:
    def __init__(self) -> None:
        self._items: dict[BookId, Book] = {}

    def get(self, book_id: BookId) -> Book:
        try:
            return self._items[book_id]
        except KeyError:
            raise DomainError(
                "Книга не найдена в репозитории."
            )

    def save(self, book: Book) -> None:
        self._items[book.id] = book


class InMemoryReaderRepository:
    def __init__(self) -> None:
        self._items: dict[ReaderId, Reader] = {}

    def get(self, reader_id: ReaderId) -> Reader:
        try:
            return self._items[reader_id]
        except KeyError:
            raise DomainError(
                "Читатель не найден в репозитории."
            )

    def save(self, reader: Reader) -> None:
        self._items[reader.id] = reader
        