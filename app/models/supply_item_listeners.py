from __future__ import annotations

from decimal import Decimal

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import SupplyItem


def _to_dec(v) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


@event.listens_for(Session, "before_flush")
def supply_item_fill_unit_price_rub(session: Session, flush_context, instances):
    """
    ЕДИНАЯ гарантия для SupplyItem:
    - unit_price_rub всегда заполнен (NOT NULL)
    - для CNY обязателен fx_rate
    Работает для Admin / API / тестов (всё, что идёт через ORM Session).
    """
    for obj in list(session.new) + list(session.dirty):
        if not isinstance(obj, SupplyItem):
            continue

        # если unit_price_rub уже задан явно — не трогаем
        if getattr(obj, "unit_price_rub", None) is not None:
            continue

        currency = getattr(obj, "currency", None)
        unit_price = _to_dec(getattr(obj, "unit_price", None))
        fx_rate = _to_dec(getattr(obj, "fx_rate", None))

        if currency is None or unit_price is None:
            continue

        if currency == "RUB":
            obj.unit_price_rub = unit_price
            continue

        if currency == "CNY":
            if fx_rate is None:
                raise ValueError("fx_rate is required for CNY items")
            obj.unit_price_rub = unit_price * fx_rate
            continue

        raise ValueError(f"Unsupported currency: {currency}")
