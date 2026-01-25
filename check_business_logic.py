import asyncio
import sys
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.db import engine
from app.models import Supplier, Warehouse, Product, Supply, SupplyItem, SupplyEvent, Batch


def ok(msg: str):
    print(f"[PASS] {msg}")


def fail(msg: str):
    print(f"[FAIL] {msg}")


def as_dec(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except Exception:
        return None


def status_name(v) -> str:
    return getattr(v, "value", v)


async def new_session() -> AsyncSession:
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


async def reload_supply(db: AsyncSession, supply_id: int) -> Supply:
    res = await db.execute(select(Supply).where(Supply.id == supply_id))
    return res.scalar_one()


async def count_batches(db: AsyncSession, supply_id: int) -> int:
    res = await db.execute(select(Batch).where(Batch.supply_id == supply_id))
    return len(res.scalars().all())


async def get_supply_items(db: AsyncSession, supply_id: int) -> list[SupplyItem]:
    res = await db.execute(select(SupplyItem).where(SupplyItem.supply_id == supply_id))
    return list(res.scalars().all())


# ------------------------
# get_or_create helpers (safe)
# ------------------------
async def _get_by_name_exact(db: AsyncSession, model, name: str):
    res = await db.execute(select(model).where(model.name == name))
    return res.scalar_one_or_none()


async def _get_by_name_fuzzy(db: AsyncSession, model, name: str):
    res = await db.execute(select(model).where(model.name.ilike(name)))
    return res.scalar_one_or_none()


async def get_or_create_named(db: AsyncSession, model, name: str):
    name_norm = name.strip()

    obj = await _get_by_name_exact(db, model, name_norm)
    if obj:
        return obj

    obj = await _get_by_name_fuzzy(db, model, name_norm)
    if obj:
        return obj

    obj = model(name=name_norm)
    db.add(obj)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        obj2 = await _get_by_name_exact(db, model, name_norm) or await _get_by_name_fuzzy(db, model, name_norm)
        if obj2:
            return obj2
        raise
    await db.refresh(obj)
    return obj


async def create_base_entities(db: AsyncSession):
    supplier = await get_or_create_named(db, Supplier, "TEST_SUPPLIER")
    wh = await get_or_create_named(db, Warehouse, "TEST_WAREHOUSE")
    p1 = await get_or_create_named(db, Product, "TEST_PRODUCT_1")
    p2 = await get_or_create_named(db, Product, "TEST_PRODUCT_2")
    return supplier, wh, p1, p2


async def create_supply(db: AsyncSession, supplier_id: int, source: str = "CN", note: str = "test") -> int:
    s = Supply(supplier_id=supplier_id, source=source, status="draft", note=note)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s.id


async def add_item(
        db: AsyncSession,
        supply_id: int,
        product_id: int,
        quantity: int,
        currency: str,
        unit_price: Decimal,
        fx_rate: Decimal | None,
):
    it = SupplyItem(
        supply_id=supply_id,
        product_id=product_id,
        quantity=quantity,
        currency=currency,
        unit_price=unit_price,
        fx_rate=fx_rate,
    )
    db.add(it)
    await db.commit()
    await db.refresh(it)
    return it.id


async def add_event(
        db: AsyncSession,
        supply_id: int,
        event_type: str,
        places_count: int | None = None,
        dest_warehouse_id: int | None = None,
        tracking_number: str | None = None,
        cost: Decimal = Decimal("0"),
        note: str | None = None,
        *,
        do_commit: bool = True,
):
    ev = SupplyEvent(
        supply_id=supply_id,
        event_type=event_type,
        places_count=places_count,
        dest_warehouse_id=dest_warehouse_id,
        tracking_number=tracking_number,
        cost=cost,
        note=note,
    )
    db.add(ev)

    if do_commit:
        await db.commit()
        await db.refresh(ev)
    else:
        await db.flush()

    return ev.id


async def must_fail(db: AsyncSession, title: str, action, contains: str | None = None):
    """
    action: coroutine, который делает flush (не commit).
    """
    try:
        async with db.begin_nested():  # SAVEPOINT
            await action
        fail(f"{title}: ожидали ошибку, но её не было")
        return False
    except Exception as e:
        await db.rollback()
        msg = str(e)
        if contains and contains not in msg:
            fail(f"{title}: ошибка есть, но текст не тот.\n  Ожидали: {contains}\n  Получили: {msg}")
            return False
        ok(f"{title}: корректно упало ({contains or 'error'})")
        return True


async def reopen_session(db: AsyncSession):
    """
    Самый надёжный сброс состояния после must_fail:
    закрыть сессию и открыть новую.
    """
    await db.close()
    return await new_session()


async def main():
    db: AsyncSession | None = None
    try:
        db = await new_session()

        r = await db.execute(text("select 1"))
        if r.scalar() != 1:
            fail("DB connection sanity check")
            sys.exit(1)
        ok("DB connection sanity check")

        supplier, wh, p1, p2 = await create_base_entities(db)
        ok("Базовые сущности готовы (get_or_create safe)")

        # ---------------------------
        # CASE A: запрет draft -> in_transit
        # ---------------------------
        sA_id = await create_supply(db, supplier.id, note="CASE_A")
        ok("CASE_A: создан Supply draft")

        await must_fail(
            db,
            "CASE_A: запрет draft -> in_transit (cargo_to_rf)",
            add_event(db, sA_id, event_type="cargo_to_rf", places_count=1, do_commit=False),
            contains="Invalid supply status transition",
        )

        # СБРОС сессии после fail-case (чтобы не было greenlet/detached)
        db = await reopen_session(db)
        supplier, wh, p1, p2 = await create_base_entities(db)

        await add_event(db, sA_id, event_type="cargo_received", places_count=1, do_commit=True)
        sA = await reload_supply(db, sA_id)
        if status_name(sA.status) == "assembled":
            ok("CASE_A: cargo_received -> assembled")
        else:
            fail(f"CASE_A: ожидали assembled, получили {status_name(sA.status)}")
            sys.exit(1)

        await add_event(db, sA_id, event_type="cargo_to_rf", places_count=1, do_commit=True)
        sA = await reload_supply(db, sA_id)
        if status_name(sA.status) == "in_transit":
            ok("CASE_A: cargo_to_rf -> in_transit")
        else:
            fail(f"CASE_A: ожидали in_transit, получили {status_name(sA.status)}")
            sys.exit(1)

        # ---------------------------
        # CASE B: received_to_wh без items
        # ---------------------------
        sB_id = await create_supply(db, supplier.id, note="CASE_B_NO_ITEMS")
        ok("CASE_B: создан Supply draft без items")

        await add_event(db, sB_id, event_type="cargo_received", places_count=1, do_commit=True)

        await must_fail(
            db,
            "CASE_B: received_to_wh без items запрещён",
            add_event(db, sB_id, event_type="received_to_wh", dest_warehouse_id=wh.id, do_commit=False),
            contains="Supply has no items",
        )

        db = await reopen_session(db)
        supplier, wh, p1, p2 = await create_base_entities(db)

        # ---------------------------
        # CASE C: received_to_wh без dest_warehouse
        # ---------------------------
        sC_id = await create_supply(db, supplier.id, note="CASE_C_NO_WH")
        ok("CASE_C: создан Supply draft")

        await add_item(
            db,
            sC_id,
            p1.id,
            quantity=10,
            currency="CNY",
            unit_price=Decimal("10"),
            fx_rate=Decimal("13"),
        )
        ok("CASE_C: добавлен SupplyItem")

        await add_event(db, sC_id, event_type="cargo_received", places_count=1, do_commit=True)

        await must_fail(
            db,
            "CASE_C: received_to_wh без dest_warehouse запрещён",
            add_event(db, sC_id, event_type="received_to_wh", dest_warehouse_id=None, do_commit=False),
            contains="dest_warehouse_id is required",
        )

        db = await reopen_session(db)
        supplier, wh, p1, p2 = await create_base_entities(db)

        # ---------------------------
        # CASE D: happy path + Batch + запрет двойного оприходования
        # ---------------------------
        sD_id = await create_supply(db, supplier.id, note="CASE_D_HAPPY")
        ok("CASE_D: создан Supply draft")

        await add_item(
            db,
            sD_id,
            p1.id,
            quantity=10,
            currency="CNY",
            unit_price=Decimal("10"),
            fx_rate=Decimal("13"),
        )
        await add_item(
            db,
            sD_id,
            p2.id,
            quantity=5,
            currency="RUB",
            unit_price=Decimal("100"),
            fx_rate=None,
        )
        ok("CASE_D: добавлены 2 SupplyItem")

        itemsD = await get_supply_items(db, sD_id)
        m = {x.product_id: x for x in itemsD}

        expected_it1 = Decimal("10") * Decimal("13")
        expected_it2 = Decimal("100")

        d1 = as_dec(getattr(m[p1.id], "unit_price_rub", None))
        d2 = as_dec(getattr(m[p2.id], "unit_price_rub", None))

        if d1 == expected_it1 and d2 == expected_it2:
            ok("CASE_D: unit_price_rub рассчитан корректно для CNY и RUB")
        else:
            fail(
                "CASE_D: unit_price_rub НЕ рассчитан/неверный.\n"
                f"  CNY ожидали {expected_it1}, получили {d1}\n"
                f"  RUB ожидали {expected_it2}, получили {d2}\n"
                "Это значит: расчёт unit_price_rub не срабатывает при создании SupplyItem."
            )
            sys.exit(1)

        await add_event(db, sD_id, event_type="cargo_received", places_count=1, do_commit=True)
        await add_event(db, sD_id, event_type="cargo_to_rf", places_count=1, do_commit=True)

        await add_event(db, sD_id, event_type="received_to_wh", dest_warehouse_id=wh.id, do_commit=True)
        sD = await reload_supply(db, sD_id)

        if status_name(sD.status) == "received":
            ok("CASE_D: received_to_wh -> received")
        else:
            fail(f"CASE_D: ожидали received, получили {status_name(sD.status)}")
            sys.exit(1)

        bcnt = await count_batches(db, sD_id)
        if bcnt == 2:
            ok("CASE_D: создалось 2 Batch (по числу SupplyItem)")
        else:
            fail(f"CASE_D: ожидали 2 Batch, получили {bcnt}")
            sys.exit(1)

        await must_fail(
            db,
            "CASE_D: повторный received_to_wh запрещён",
            add_event(db, sD_id, event_type="received_to_wh", dest_warehouse_id=wh.id, do_commit=False),
            contains="Batches already created",
        )

        ok("ВСЕ ПРОВЕРКИ 4.2 ПРОЙДЕНЫ ✅")

    finally:
        try:
            if db is not None:
                await db.close()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit:
        raise
    except Exception as e:
        print("[FATAL]", e)
        sys.exit(1)
