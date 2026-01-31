from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Какая закупочная поставка породила эту партию
    supply_id: Mapped[int] = mapped_column(
        ForeignKey("supplies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Количество единиц в партии (фиксируется при оприходовании)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Итоговая себестоимость единицы (цена закупки + доля карго + доля ТК)
    unit_cost_final: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    supply = relationship("Supply")
    product = relationship("Product")
    warehouse = relationship("Warehouse")

    def __str__(self) -> str:
        return f"Batch #{self.id} | Supply #{self.supply_id} | Product #{self.product_id} | Qty {self.quantity}"
