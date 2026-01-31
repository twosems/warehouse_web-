from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Sequence

from app.models.batch import Batch


def _to_decimal(x) -> Decimal:
    if x is None:
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def allocate_logistics_cost(
        batches: Sequence[Batch],
        total_cost: Decimal | int | float,
) -> None:
    """
    Распределяет total_cost по batches пропорционально стоимости партии:
        weight_i = quantity_i * unit_cost_final_i

    Результат записывается прямо в Batch.unit_cost_final (увеличиваем на долю логистики на единицу).

    ВАЖНО:
    - делаем округление до 2 знаков (как деньги)
    - следим за тем, чтобы суммарно распределение совпало с total_cost:
      остаток копеек докидываем в самую "тяжёлую" партию.
    """
    total_cost_dec = _to_decimal(total_cost)
    if total_cost_dec <= 0:
        return
    if not batches:
        return

    # вес каждой партии: qty * себестоимость_ед
    weights: list[Decimal] = []
    for b in batches:
        qty = _to_decimal(getattr(b, "quantity", 0))
        unit = _to_decimal(getattr(b, "unit_cost_final", 0))
        w = qty * unit
        weights.append(w)

    total_weight = sum(weights)
    if total_weight <= 0:
        # fallback: если нечего взвешивать — распределим по количеству
        weights = [_to_decimal(getattr(b, "quantity", 0)) for b in batches]
        total_weight = sum(weights)

    if total_weight <= 0:
        return

    # распределяем total_cost по партиям, округляя до копеек на "партию"
    # затем превращаем в добавку на единицу.
    allocated_per_batch: list[Decimal] = []
    for w in weights:
        share = (total_cost_dec * w) / total_weight
        share = share.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        allocated_per_batch.append(share)

    # поправка из-за округления: добьём разницу в самую тяжёлую партию
    allocated_sum = sum(allocated_per_batch)
    diff = (total_cost_dec - allocated_sum).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if diff != 0:
        idx_max = max(range(len(weights)), key=lambda i: weights[i])
        allocated_per_batch[idx_max] = (allocated_per_batch[idx_max] + diff).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # применяем к batches как добавку к unit_cost_final на единицу
    for b, add_cost in zip(batches, allocated_per_batch):
        qty = _to_decimal(getattr(b, "quantity", 0))
        if qty <= 0:
            continue

        add_per_unit = (add_cost / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        current = _to_decimal(getattr(b, "unit_cost_final", 0))
        b.unit_cost_final = (current + add_per_unit).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
