from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, delete, update

from app.core.db import AsyncSessionLocal
from app.models.product import Product
from app.schemas.product import (
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from app.admin import setup_admin
from app.schemas.supply import SupplyCreate
from app.services.supply_service import create_supply
from fastapi import HTTPException

from app.schemas.supply_event import SupplyEventCreate
from app.services.supply_service import add_supply_event
from app.models import Supply

# --------------------
# FastAPI app
# --------------------
app = FastAPI(title="Warehouse System", debug=True)

# Подключаем SQLAdmin
setup_admin(app)


# --------------------
# DB dependency
# --------------------
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# --------------------
# PRODUCTS CRUD
# --------------------

@app.post("/products", response_model=ProductOut)
async def create_product(
        data: ProductCreate,
        db: AsyncSession = Depends(get_db),
):
    stmt = insert(Product).values(name=data.name).returning(Product)
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


@app.get("/products", response_model=list[ProductOut])
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).order_by(Product.id))
    return result.scalars().all()


@app.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@app.patch("/products/{product_id}", response_model=ProductOut)
async def update_product(
        product_id: int,
        data: ProductUpdate,
        db: AsyncSession = Depends(get_db),
):
    stmt = (
        update(Product)
        .where(Product.id == product_id)
        .values(**data.model_dump(exclude_unset=True))
        .returning(Product)
    )

    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.commit()
    return product


@app.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        delete(Product)
        .where(Product.id == product_id)
        .returning(Product.id)
    )
    deleted_id = result.scalar_one_or_none()

    if deleted_id is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.commit()
@app.post("/supplies", response_model=dict)
async def create_supply_api(
        data: SupplyCreate,
        db: AsyncSession = Depends(get_db),
):
    supply = await create_supply(db, data)
    await db.commit()
    await db.refresh(supply)

    return {
        "id": supply.id,
        "status": supply.status,
    }

@app.post("/supplies/{supply_id}/events", response_model=dict)
async def create_supply_event_api(
        supply_id: int,
        data: SupplyEventCreate,
        db: AsyncSession = Depends(get_db),
):
    supply = await db.get(Supply, supply_id)
    if not supply:
        raise HTTPException(status_code=404, detail="Supply not found")

    try:
        supply = await add_supply_event(
            db=db,
            supply=supply,
            data=data,
        )
        await db.commit()
        await db.refresh(supply)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": supply.id,
        "status": supply.status,
    }
