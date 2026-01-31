from __future__ import annotations

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class MarketplaceShipmentItem(Base):
    __tablename__ = "marketplace_shipment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("marketplace_shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    shipment = relationship("MarketplaceShipment", back_populates="items")
    product = relationship("Product")
