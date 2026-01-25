from pydantic import BaseModel, Field
from typing import List, Literal


class SupplyItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    currency: Literal["RUB", "CNY"]
    unit_price: float = Field(gt=0)
    fx_rate: float | None = Field(default=None, gt=0)


class SupplyCreate(BaseModel):
    supplier_id: int
    source: Literal["RU", "CN"]
    note: str | None = None
    items: List[SupplyItemCreate]
