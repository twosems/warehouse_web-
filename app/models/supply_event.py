from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base
from app.models.enums import SupplyEventType


class SupplyEvent(Base):
    __tablename__ = "supply_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    supply_id: Mapped[int] = mapped_column(
        ForeignKey("supplies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Тип события:
    # cargo_received  - "Принят карго" (Китай) -> places_count обязателен
    # cargo_to_rf     - "Доставляется в Россию" (опционально как событие, если нужно)
    # passed_to_tk    - "Передан в ТК" -> dest_warehouse_id обязателен
    # received_to_wh  - "Оприходован" (можно фиксировать событием)
    event_type: Mapped[SupplyEventType] = mapped_column(
        Enum(SupplyEventType, name="supply_event_type"),
        nullable=False,
        index=True,
    )

    places_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    dest_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    supply = relationship("Supply")
    dest_warehouse = relationship("Warehouse")
