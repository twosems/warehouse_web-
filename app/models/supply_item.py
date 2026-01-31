from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class SupplyItem(Base):
    __tablename__ = "supply_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    supply_id: Mapped[int] = mapped_column(
        ForeignKey("supplies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Цена за единицу в исходной валюте
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Валюта: RUB или CNY
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Курс для CNY (если RUB — можно хранить 1.0)
    fx_rate: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=1)

    # Цена за единицу в рублях (зафиксированное/расчётное значение)
    unit_price_rub: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    supply = relationship("Supply")
    product = relationship("Product")

    def __str__(self) -> str:
        return f"Supply #{self.supply_id} → Product #{self.product_id} x {self.quantity}"
