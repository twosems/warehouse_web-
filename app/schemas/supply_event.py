from pydantic import BaseModel, Field


class SupplyEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=30)

    places_count: int | None = None
    dest_warehouse_id: int | None = None
    tracking_number: str | None = Field(default=None, max_length=100)
    cost: float = 0
    note: str | None = None
