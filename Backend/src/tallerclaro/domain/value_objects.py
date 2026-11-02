"""Objetos de valor del dominio."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


class Money:
    """Importe monetario en USD con redondeo a dos decimales."""

    __slots__ = ("_amount",)

    def __init__(self, amount: Decimal | float | str | int) -> None:
        self._amount = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def amount(self) -> Decimal:
        return self._amount

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount == other._amount

    def __lt__(self, other: Money) -> bool:
        return self._amount < other._amount

    def __le__(self, other: Money) -> bool:
        return self._amount <= other._amount

    def __gt__(self, other: Money) -> bool:
        return self._amount > other._amount

    def __ge__(self, other: Money) -> bool:
        return self._amount >= other._amount

    def __add__(self, other: Money) -> Money:
        return Money(self._amount + other._amount)

    def __sub__(self, other: Money) -> Money:
        return Money(self._amount - other._amount)

    def __mul__(self, other: Decimal | float | str | int) -> Money:
        return Money(self._amount * Decimal(other))

    def __repr__(self) -> str:
        return f"Money({self._amount})"

    def is_positive(self) -> bool:
        return self._amount > Decimal("0")

    def is_non_negative(self) -> bool:
        return self._amount >= Decimal("0")

    @classmethod
    def zero(cls) -> Money:
        return cls(Decimal("0"))
