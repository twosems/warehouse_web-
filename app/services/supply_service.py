from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Supply, SupplyItem, SupplyEvent
from app.models.enums import SupplyStatus
from app.schemas.supply import SupplyCreate


async def create_supply(db: AsyncSession, data: SupplyCreate) -> Supply:
    """
    Создание поставки + позиций (БЕЗ commit внутри).
    commit делает роутер/верхний слой.

    unit_price_rub можно считать и тут, но даже если забыть —
    listener supply_item_listeners гарантирует заполнение.
    """
    supply = Supply(
        supplier_id=data.supplier_id,
        source=data.source,
        status=SupplyStatus.draft,
        note=data.note,
    )
    db.add(supply)
    await db.flush()  # supply.id

    for item in data.items:
        db.add(
            SupplyItem(
                supply_id=supply.id,
                product_id=item.product_id,
                quantity=item.quantity,
                currency=item.currency,
                unit_price=item.unit_price,
                fx_rate=item.fx_rate,
                # unit_price_rub НЕ обязаны ставить — listener заполнит
            )
        )

    await db.flush()
    await db.refresh(supply)
    return supply


async def add_supply_event(db: AsyncSession, supply: Supply, data: "SupplyEventCreate") -> Supply:
    """
    ВАРИАНТ 2: сервис только создаёт событие.
    Статус supply и Batch'и изменит/создаст listener (before_flush).
    """
    event = SupplyEvent(
        supply_id=supply.id,
        event_type=data.event_type,
        places_count=data.places_count,
        dest_warehouse_id=data.dest_warehouse_id,
        tracking_number=data.tracking_number,
        cost=data.cost,
        note=data.note,
    )
    db.add(event)

    await db.flush()
    await db.refresh(supply)
    return supply
