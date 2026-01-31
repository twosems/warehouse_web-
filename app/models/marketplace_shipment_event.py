from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base
from app.models.enums import MarketplaceShipmentEventType


class MarketplaceShipmentEvent(Base):
    __tablename__ = "marketplace_shipment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("marketplace_shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[MarketplaceShipmentEventType] = mapped_column(
        Enum(MarketplaceShipmentEventType, name="mp_shipment_event_type"),
        nullable=False,
        index=True,
    )

    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    shipment = relationship("MarketplaceShipment", back_populates="events")
