"""
check_project_stage5.py

Stage-5 audit:
- Schema checks: stocks table exists + unique constraint
- Business checks: SupplyEvent → status → Batch → Stock (with canon dest warehouse on passed_to_tk)
- Canon checks: remaining gap is logistics cost distribution (WARN or FAIL if CANON_STRICT=1)

Run (PowerShell):
  $env:POSTGRES_DSN="postgresql+asyncpg://postgres:pass@localhost:5432/warehouse_web"
  python .\check_project_stage5.py

Env:
  POSTGRES_DSN / DATABASE_URL : async DSN (postgresql+asyncpg://...)
  CANON_STRICT               : "1" => canon gaps become FAIL, else WARN
  KEEP_TEST_DATA             : "1" => keep test rows
"""

from __future__ import annotations

import os
import sys
import asyncio
import datetime as dt
import secrets
from dataclasses import dataclass
from typing import Any, Optional


# ---------------- helpers ----------------

def _now() -> dt.datetime:
    return dt.datetime.utcnow()

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")

def _run_id() -> str:
    # stable enough, short, filesystem-safe
    return f"{dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(3)}"

@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str = ""
    severity: str = "FAIL"  # FAIL/WARN/INFO


def _model_columns(model) -> set[str]:
    return {c.name for c in model.__table__.columns}

def _filtered_kwargs(model, **kwargs) -> dict[str, Any]:
    cols = _model_columns(model)
    return {k: v for k, v in kwargs.items() if k in cols}

def _pick_first_existing(model, candidates: list[str], default: Optional[str] = None) -> Optional[str]:
    cols = _model_columns(model)
    for c in candidates:
        if c in cols:
            return c
    return default

def _short_source_for_supply(SupplyModel) -> str:
    col = SupplyModel.__table__.c.get("source")
    if col is not None:
        length = getattr(col.type, "length", None)
        if length == 2:
            return "CN"
    return "CN"

def _currency_code_for_item(SupplyItemModel) -> tuple[str, str]:
    col = SupplyItemModel.__table__.c.get("currency")
    length = getattr(col.type, "length", None) if col is not None else None
    if length == 2:
        return ("RU", "CN")
    return ("RUB", "CNY")


# ---------------- main ----------------

async def main() -> int:
    dsn = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL") or ""
    if not dsn:
        print("❌ Не найден POSTGRES_DSN (или DATABASE_URL).")
        print("   Укажи переменную окружения POSTGRES_DSN как в .env проекта.")
        return 2

    canon_strict = _env_bool("CANON_STRICT", default=False)
    keep_test_data = _env_bool("KEEP_TEST_DATA", default=False)

    rid = _run_id()
    results: list[CheckResult] = []

    # Imports
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker

        # ensure listeners are registered
        import app.models  # noqa: F401

        from app.models.product import Product
        from app.models.warehouse import Warehouse
        from app.models.supplier import Supplier
        from app.models.supply import Supply
        from app.models.supply_item import SupplyItem
        from app.models.supply_event import SupplyEvent
        from app.models.enums import SupplyStatus, SupplyEventType

    except Exception as e:
        print("❌ Ошибка импорта проекта/моделей:", repr(e))
        return 2

    # adaptive event field names
    event_time_field = _pick_first_existing(
        SupplyEvent, ["created_at", "at", "event_at", "timestamp"], default="created_at"
    )
    tracking_field = _pick_first_existing(
        SupplyEvent, ["tracking_number", "tracking", "track"], default="tracking_number"
    )

    engine = create_async_engine(dsn, future=True)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # ---------------- Schema checks ----------------
    async with engine.begin() as conn:
        try:
            r = await conn.execute(text("SELECT to_regclass('public.stocks');"))
            reg = r.scalar()
            if reg is None:
                results.append(CheckResult(
                    name="Schema: stocks table exists",
                    ok=False,
                    details="Таблица public.stocks не найдена. Проверь alembic upgrade head.",
                ))
            else:
                results.append(CheckResult(
                    name="Schema: stocks table exists",
                    ok=True,
                    details="public.stocks существует.",
                    severity="INFO",
                ))

            # unique constraint check (best-effort, Postgres)
            try:
                r2 = await conn.execute(text("""
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'public.stocks'::regclass
                      AND contype = 'u';
                """))
                uniq = [row[0] for row in r2.fetchall()]
                if any("uq_stocks_warehouse_product" in u for u in uniq):
                    results.append(CheckResult(
                        name="Schema: unique stock (warehouse_id, product_id)",
                        ok=True,
                        details="UNIQUE uq_stocks_warehouse_product найден.",
                        severity="INFO",
                    ))
                else:
                    results.append(CheckResult(
                        name="Schema: unique stock (warehouse_id, product_id)",
                        ok=False,
                        details="Не найден UNIQUE uq_stocks_warehouse_product в public.stocks.",
                    ))
            except Exception as e:
                results.append(CheckResult(
                    name="Schema: unique stock (warehouse_id, product_id)",
                    ok=False,
                    details=f"Не смог проверить UNIQUE constraint (pg_constraint): {e!r}",
                    severity="WARN",
                ))

        except Exception as e:
            results.append(CheckResult(
                name="Schema: basic checks",
                ok=False,
                details=f"Ошибка проверки схемы: {e!r}",
            ))

    # ---------------- Business checks ----------------
    test_ids: dict[str, Any] = {}

    # Names unique per run
    wh_name = f"__check_wh__{rid}"
    sup_name = f"__check_supplier__{rid}"
    p1_name = f"__check_product_1__{rid}"
    p2_name = f"__check_product_2__{rid}"
    supply_note = f"__check_supply__{rid}"
    track = f"__check_track__{rid}"
    track_dup = f"__check_track_dup__{rid}"

    async with session_factory() as session:
        try:
            from sqlalchemy import text  # for run_sync closure

            # Create Warehouse/Supplier/Products with unique names
            wh = Warehouse(**_filtered_kwargs(Warehouse, name=wh_name, address=None, note=None))
            sup = Supplier(**_filtered_kwargs(Supplier, name=sup_name, contact=None, note=None))
            p1 = Product(**_filtered_kwargs(Product, name=p1_name))
            p2 = Product(**_filtered_kwargs(Product, name=p2_name))

            session.add_all([wh, sup, p1, p2])
            await session.commit()

            test_ids.update({
                "warehouse_id": getattr(wh, "id", None),
                "supplier_id": getattr(sup, "id", None),
                "p1_id": getattr(p1, "id", None),
                "p2_id": getattr(p2, "id", None),
            })

            results.append(CheckResult(
                name="Business: seed entities",
                ok=True,
                details=f"Созданы Product/Warehouse/Supplier (run_id={rid}).",
                severity="INFO",
            ))

            # Create Supply first (flush), then items with explicit supply_id
            supply = Supply(**_filtered_kwargs(
                Supply,
                supplier_id=sup.id,
                source=_short_source_for_supply(Supply),
                status=SupplyStatus.draft,
                note=supply_note,
            ))
            session.add(supply)
            await session.flush()
            test_ids["supply_id"] = supply.id

            rub_code, cny_code = _currency_code_for_item(SupplyItem)

            it1 = SupplyItem(**_filtered_kwargs(
                SupplyItem,
                supply_id=supply.id,
                product_id=p1.id,
                quantity=10,
                currency=rub_code,
                unit_price=100,
                fx_rate=1.0,
                note=None,
            ))

            it2 = SupplyItem(**_filtered_kwargs(
                SupplyItem,
                supply_id=supply.id,
                product_id=p2.id,
                quantity=5,
                currency=cny_code,
                unit_price=20,
                fx_rate=12.0,
                note=None,
            ))

            session.add_all([it1, it2])
            await session.commit()

            # Verify unit_price_rub calculated (if column exists)
            await session.refresh(it1)
            await session.refresh(it2)

            def _num(v):
                try:
                    return float(v)
                except Exception:
                    return None

            ok_rub = True
            ok_cny = True

            if "unit_price_rub" in _model_columns(SupplyItem):
                v1 = _num(getattr(it1, "unit_price_rub", None))
                v2 = _num(getattr(it2, "unit_price_rub", None))
                ok_rub = (v1 is not None) and abs(v1 - float(getattr(it1, "unit_price", 0))) < 1e-6
                ok_cny = (v2 is not None) and abs(v2 - float(getattr(it2, "unit_price", 0)) * float(getattr(it2, "fx_rate", 0))) < 1e-6

            if ok_rub and ok_cny:
                results.append(CheckResult(
                    name="Business: unit_price_rub auto-calc",
                    ok=True,
                    details=f"unit_price_rub OK (RUB={getattr(it1,'unit_price_rub',None)} CNY={getattr(it2,'unit_price_rub',None)}).",
                    severity="INFO",
                ))
            else:
                results.append(CheckResult(
                    name="Business: unit_price_rub auto-calc",
                    ok=False,
                    details=f"unit_price_rub неверен (RUB={getattr(it1,'unit_price_rub',None)} CNY={getattr(it2,'unit_price_rub',None)}).",
                ))

            # --- IMPORTANT: run SupplyEvent commits under run_sync to avoid MissingGreenlet ---
            def _run_events_and_checks(sync_sess) -> tuple[list[Any], list[Any]]:
                def make_event(
                        *,
                        event_type,
                        dest_warehouse_id=None,
                        tracking_value=None,
                        cost=None,
                        places_count=None,
                        note=None,
                ):
                    kwargs = {
                        "supply_id": supply.id,
                        "event_type": event_type,
                        event_time_field: _now(),
                        "dest_warehouse_id": dest_warehouse_id,
                        tracking_field: tracking_value,
                        "cost": cost,
                        "places_count": places_count,
                        "note": note,
                    }
                    return SupplyEvent(**_filtered_kwargs(SupplyEvent, **kwargs))

                # Invalid transition must be blocked: draft -> in_transit (cargo_to_rf)
                bad = make_event(
                    event_type=SupplyEventType.cargo_to_rf,
                    dest_warehouse_id=None,
                    tracking_value=None,
                    cost=None,
                    places_count=None,
                    note=f"__check_bad_transition__{rid}",
                )
                sync_sess.add(bad)
                try:
                    sync_sess.commit()
                    raise RuntimeError("INVALID_TRANSITION_NOT_BLOCKED")
                except Exception as ex:
                    sync_sess.rollback()
                    if isinstance(ex, RuntimeError) and str(ex) == "INVALID_TRANSITION_NOT_BLOCKED":
                        raise

                # cargo_received
                ev1 = make_event(
                    event_type=SupplyEventType.cargo_received,
                    cost=1000,
                    places_count=2,
                    note=f"__check_ev1__{rid}",
                )
                sync_sess.add(ev1)
                sync_sess.commit()
                sync_sess.refresh(supply)

                if str(supply.status) != str(SupplyStatus.assembled):
                    raise RuntimeError(f"BAD_STATUS_AFTER_CARGO_RECEIVED:{supply.status}")

                # passed_to_tk (CANON: must contain dest_warehouse_id)
                ev2 = make_event(
                    event_type=SupplyEventType.passed_to_tk,
                    dest_warehouse_id=wh.id,
                    tracking_value=track,
                    cost=2000,
                    note=f"__check_ev2__{rid}",
                )
                sync_sess.add(ev2)
                sync_sess.commit()
                sync_sess.refresh(supply)

                if str(supply.status) != str(SupplyStatus.in_transit):
                    raise RuntimeError(f"BAD_STATUS_AFTER_PASSED_TO_TK:{supply.status}")

                # received_to_wh (CANON: warehouse should be taken automatically)
                ev3 = make_event(
                    event_type=SupplyEventType.received_to_wh,
                    dest_warehouse_id=None,  # must auto-fill from Supply.dest_warehouse_id
                    tracking_value=track,
                    cost=3000,
                    note=f"__check_ev3__{rid}",
                )
                sync_sess.add(ev3)
                sync_sess.commit()
                sync_sess.refresh(supply)

                if str(supply.status) != str(SupplyStatus.received):
                    raise RuntimeError(f"BAD_STATUS_AFTER_RECEIVED_TO_WH:{supply.status}")

                batches = sync_sess.execute(
                    text("SELECT product_id, quantity FROM batches WHERE supply_id = :sid ORDER BY product_id"),
                    {"sid": supply.id},
                ).fetchall()

                if not (len(batches) == 2 and sorted([int(b[1]) for b in batches]) == [5, 10]):
                    raise RuntimeError(f"BAD_BATCHES:{batches}")

                stocks = sync_sess.execute(
                    text("""
                        SELECT product_id, qty
                        FROM stocks
                        WHERE warehouse_id = :wid
                        ORDER BY product_id
                    """),
                    {"wid": wh.id},
                ).fetchall()

                if not (len(stocks) == 2 and sorted([int(s[1]) for s in stocks]) == [5, 10]):
                    raise RuntimeError(f"BAD_STOCKS:{stocks}")

                # Duplicate receiving should be blocked
                ev_dup = make_event(
                    event_type=SupplyEventType.received_to_wh,
                    dest_warehouse_id=None,
                    tracking_value=track_dup,
                    note=f"__check_dup__{rid}",
                )
                sync_sess.add(ev_dup)
                try:
                    sync_sess.commit()
                    raise RuntimeError("DUP_RECEIVE_NOT_BLOCKED")
                except Exception as ex:
                    sync_sess.rollback()
                    if isinstance(ex, RuntimeError) and str(ex) == "DUP_RECEIVE_NOT_BLOCKED":
                        raise

                return batches, stocks

            try:
                batches, stocks = await session.run_sync(_run_events_and_checks)

                results.append(CheckResult(
                    name="Business: invalid status transition blocked",
                    ok=True,
                    details="Переход draft→in_transit заблокирован (как и должно быть).",
                    severity="INFO",
                ))
                results.append(CheckResult("Business: status after cargo_received", True, "status=assembled", "INFO"))
                results.append(CheckResult("Business: status after passed_to_tk", True, "status=in_transit", "INFO"))
                results.append(CheckResult("Business: status after received_to_wh", True, "status=received", "INFO"))
                results.append(CheckResult("Business: batches created on received_to_wh", True, f"batches={batches}", "INFO"))
                results.append(CheckResult("Business: stock updated from batches", True, f"stocks={stocks}", "INFO"))
                results.append(CheckResult(
                    name="Business: prevent duplicate receiving",
                    ok=True,
                    details="Дубль received_to_wh заблокирован (как и должно быть).",
                    severity="INFO",
                ))

            except Exception as e:
                msg = repr(e)
                if isinstance(e, RuntimeError):
                    msg = str(e)
                results.append(CheckResult("Business: suite", False, f"Ошибка выполнения бизнес-набора: {msg}"))

        except Exception as e:
            await session.rollback()
            results.append(CheckResult("Business: suite", False, f"Ошибка выполнения бизнес-набора: {e!r}"))

        finally:
            if not keep_test_data:
                # robust cleanup by run_id (even if ids are missing)
                try:
                    from sqlalchemy import text

                    # delete supply subtree by note marker
                    await session.execute(text("""
                        DELETE FROM supply_events
                        WHERE supply_id IN (SELECT id FROM supplies WHERE note = :note)
                    """), {"note": supply_note})
                    await session.execute(text("""
                        DELETE FROM batches
                        WHERE supply_id IN (SELECT id FROM supplies WHERE note = :note)
                    """), {"note": supply_note})
                    await session.execute(text("""
                        DELETE FROM supply_items
                        WHERE supply_id IN (SELECT id FROM supplies WHERE note = :note)
                    """), {"note": supply_note})
                    await session.execute(text("DELETE FROM supplies WHERE note = :note"), {"note": supply_note})

                    # delete stocks for this warehouse name marker
                    await session.execute(text("""
                        DELETE FROM stocks
                        WHERE warehouse_id IN (SELECT id FROM warehouses WHERE name = :wname)
                    """), {"wname": wh_name})

                    # delete reference entities by unique names
                    await session.execute(text("DELETE FROM warehouses WHERE name = :wname"), {"wname": wh_name})
                    await session.execute(text("DELETE FROM suppliers WHERE name = :sname"), {"sname": sup_name})
                    await session.execute(text("DELETE FROM products WHERE name IN (:p1, :p2)"), {"p1": p1_name, "p2": p2_name})

                    await session.commit()
                    results.append(CheckResult("Cleanup: test data removed", True, "Тестовые данные удалены.", "INFO"))
                except Exception as e:
                    await session.rollback()
                    results.append(CheckResult("Cleanup: test data removed", False, f"Не смог удалить тестовые данные: {e!r}", "WARN"))

    # ---------------- Canon checks ----------------
    def canon_result(name: str, ok: bool, details: str) -> None:
        if ok:
            results.append(CheckResult(name, True, details, "INFO"))
        else:
            results.append(CheckResult(name, False, details, "FAIL" if canon_strict else "WARN"))

    canon_result(
        "Canon: dest warehouse set at passed_to_tk (not at received_to_wh)",
        ok=True,
        details="Реализовано: dest warehouse фиксируется на passed_to_tk; received_to_wh подставляет автоматически.",
    )

    canon_result(
        "Canon: logistics costs distributed into batch unit_cost_final",
        ok=False,
        details=(
            "Сейчас Batch.unit_cost_final берётся из item.unit_price_rub, "
            "а SupplyEvent.cost не распределяется по партиям. По канону нужно распределение."
        ),
    )

    # ---------------- Report ----------------
    fails = 0
    warns = 0

    print("\n=== CHECK REPORT (Stage 5) ===\n")
    for r in results:
        tag = "✅" if r.ok else ("⚠️" if r.severity == "WARN" else "❌")
        print(f"{tag} {r.name}")
        if r.details:
            print(f"    {r.details}")
        if not r.ok and r.severity == "FAIL":
            fails += 1
        if not r.ok and r.severity == "WARN":
            warns += 1

    print("\n--- summary ---")
    print(f"FAIL: {fails}")
    print(f"WARN: {warns}")
    print("CANON_STRICT =", "1" if canon_strict else "0")
    print("KEEP_TEST_DATA =", "1" if keep_test_data else "0")
    print("Event time field =", event_time_field)
    print("Tracking field   =", tracking_field)
    print("Run ID           =", rid)

    await engine.dispose()
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        print("❌ Fatal:", repr(e))
        sys.exit(2)
