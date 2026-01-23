from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str


class ProductOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

from typing import Optional
from pydantic import BaseModel

class ProductUpdate(BaseModel):
    name: Optional[str] = None
