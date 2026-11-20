from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4
import re


class DomainError(Exception):
    """Базовое исключение доменного слоя."""


class DomainInvariantViolation(DomainError):
    """Ошибка нарушения бизнес-правила."""


class InvalidValueObject(DomainError):
    """Ошибка некорректного значения объекта-значения."""


@dataclass(frozen=True, slots=True)
class BookId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObject(
                "Идентификатор книги должен быть UUID."
            )

    @classmethod
    def new(cls) -> "BookId":
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class ReaderId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObject(
                "Идентификатор читателя должен быть UUID."
            )

    @classmethod
    def new(cls) -> "ReaderId":
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class ISBN:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidValueObject(
                "ISBN должен быть строковым значением."
            )

        normalized_value = (
            self.value.replace("-", "").replace(" ", "")
        )

        if not re.fullmatch(r"\d{10}|\d{13}", normalized_value):
            raise InvalidValueObject(
                "ISBN должен содержать 10 или 13 цифр."
            )

        object.__setattr__(self, "value", normalized_value)


@dataclass(frozen=True, slots=True)
class LoanPeriod:
    days: int

    def __post_init__(self) -> None:
        if isinstance(self.days, bool) or not isinstance(self.days, int):
            raise InvalidValueObject(
                "Срок выдачи должен быть целым числом дней."
            )

        if not 1 <= self.days <= 30:
            raise InvalidValueObject(
                "Срок выдачи должен находиться от 1 до 30 дней."
            )


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str = "RUB"

    def __post_init__(self) -> None:
        try:
            normalized_amount = Decimal(str(self.amount))
        except (InvalidOperation, ValueError):
            raise InvalidValueObject(
                "Сумма должна быть корректным числом."
            )

        if not normalized_amount.is_finite():
            raise InvalidValueObject(
                "Сумма должна быть конечным числом."
            )

        if normalized_amount < 0:
            raise InvalidValueObject(
                "Сумма не может быть отрицательной."
            )

        if self.currency != "RUB":
            raise InvalidValueObject(
                "В модели поддерживается только валюта RUB."
            )

        object.__setattr__(self, "amount", normalized_amount)
        