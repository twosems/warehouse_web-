from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    def __str__(self) -> str:
        return f"[{self.id}] {self.name}"
