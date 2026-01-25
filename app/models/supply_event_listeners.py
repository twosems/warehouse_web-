from __future__ import annotations

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import Batch, Supply, SupplyEvent, SupplyItem
from app.models.enums import SupplyEventType
from app.services.supply_events_map import EVENT_TYPE_TO_STATUS
from app.services.supply_transitions import validate_supply_transition


@event.listens_for(Session, "before_flush")
def supply_apply_status_and_batches(session: Session, flush_context, instances):
    """
    ЕДИНЫЙ источник истины для SupplyEvent:
    - меняет Supply.status по событию (через EVENT_TYPE_TO_STATUS)
    - проверяет допустимость перехода (validate_supply_transition)
    - при received_to_wh создаёт Batch'и и защищает от дубля

    ВАЖНО: работаем с Enum SupplyEventType, не со строками.
    """

    for obj in session.new:
        if not isinstance(obj, SupplyEvent):
            continue

        supply = session.get(Supply, obj.supply_id)
        if not supply:
            continue

        event_type = obj.event_type  # Enum: SupplyEventType

        # 0) Preconditions для received_to_wh (чтобы ошибки были "по делу")
        if event_type == SupplyEventType.received_to_wh:
            if not obj.dest_warehouse_id:
                raise ValueError("dest_warehouse_id is required for received_to_wh")

            existing = session.execute(
                select(Batch.id).where(Batch.supply_id == supply.id).limit(1)
            ).first()
            if existing:
                raise ValueError("Batches already created for this supply")

            items = session.execute(
                select(SupplyItem).where(SupplyItem.supply_id == supply.id)
            ).scalars().all()

            if not items:
                raise ValueError("Supply has no items")

        # 1) Статус по карте событий
        new_status = EVENT_TYPE_TO_STATUS.get(event_type)
        if new_status is None:
            continue

        # 2) Валидация перехода
        validate_supply_transition(supply.status, new_status)

        supply.status = new_status
        session.add(supply)

        # 3) Создание Batch при оприходовании
        if event_type == SupplyEventType.received_to_wh:
            items = session.execute(
                select(SupplyItem).where(SupplyItem.supply_id == supply.id)
            ).scalars().all()

            for it in items:
                session.add(
                    Batch(
                        supply_id=supply.id,
                        product_id=it.product_id,
                        warehouse_id=obj.dest_warehouse_id,
                        quantity=it.quantity,
                        unit_cost_final=it.unit_price_rub,
                    )
                )
