from __future__ import annotations

from typing import Mapping

from aggregates import Book, Reader


class AggregateFactory:
    @staticmethod
    def restore_book(
        state: Mapping[str, object],
    ) -> Book:
        return Book.from_state(dict(state))

    @staticmethod
    def restore_reader(
        state: Mapping[str, object],
    ) -> Reader:
        return Reader.from_state(dict(state))
        