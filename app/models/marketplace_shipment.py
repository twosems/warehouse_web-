from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base
from app.models.enums import MarketplaceShipmentStatus, MarketplaceType


class MarketplaceShipment(Base):
    __tablename__ = "marketplace_shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    marketplace: Mapped[MarketplaceType] = mapped_column(
        Enum(MarketplaceType, name="marketplace_type"),
        nullable=False,
        index=True,
    )

    # откуда списываем (твой склад, например Томск)
    source_warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # куда едет (склад WB/Ozon)
    marketplace_warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("marketplace_warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[MarketplaceShipmentStatus] = mapped_column(
        Enum(MarketplaceShipmentStatus, name="mp_shipment_status"),
        nullable=False,
        default=MarketplaceShipmentStatus.draft,
        server_default="draft",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    source_warehouse = relationship("Warehouse")
    marketplace_warehouse = relationship("MarketplaceWarehouse")
    items = relationship("MarketplaceShipmentItem", back_populates="shipment", cascade="all, delete-orphan")
    events = relationship("MarketplaceShipmentEvent", back_populates="shipment", cascade="all, delete-orphan")
