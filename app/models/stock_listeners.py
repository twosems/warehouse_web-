from datetime import datetime

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import Batch
from app.models.stock import Stock


@event.listens_for(Session, "before_flush")
def stock_apply_on_batch(session: Session, flush_context, instances):
    """
    Единый источник истины по остаткам:
    - появление Batch увеличивает Stock.qty
    - удаление Batch уменьшает Stock.qty (защита от минуса)
    """
    # --- NEW batches: +qty ---
    for obj in session.new:
        if not isinstance(obj, Batch):
            continue

        stock = session.execute(
            select(Stock).where(
                Stock.warehouse_id == obj.warehouse_id,
                Stock.product_id == obj.product_id,
                )
        ).scalar_one_or_none()

        if stock is None:
            stock = Stock(
                warehouse_id=obj.warehouse_id,
                product_id=obj.product_id,
                qty=0,
            )
            session.add(stock)

        stock.qty = int(stock.qty) + int(obj.quantity)
        stock.updated_at = datetime.utcnow()
        session.add(stock)

    # --- DELETED batches: -qty ---
    for obj in session.deleted:
        if not isinstance(obj, Batch):
            continue

        stock = session.execute(
            select(Stock).where(
                Stock.warehouse_id == obj.warehouse_id,
                Stock.product_id == obj.product_id,
                )
        ).scalar_one_or_none()

        if stock is None:
            raise ValueError("Stock row not found for deleted batch (data inconsistency)")

        new_qty = int(stock.qty) - int(obj.quantity)
        if new_qty < 0:
            raise ValueError("Stock cannot be negative")

        stock.qty = new_qty
        stock.updated_at = datetime.utcnow()
        session.add(stock)
