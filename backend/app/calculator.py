"""
Nutrient intake calculator (thesis objective 2).

Given a list of food-diary entries (food_code, quantity, unit, optional meal),
this resolves each to grams, looks up per-100g nutrient composition from the DB,
scales it, and aggregates total daily intake per nutrient across all entries.
"""
from collections import defaultdict

from .cooking_yield import adjust_value
from .db import get_conn
from .portions import to_grams, PortionConversionError
from .schemas import DiaryInput, EntryResolution, IntakeResult, NutrientTotal


def calculate_intake(diary: DiaryInput) -> IntakeResult:
    conn = get_conn()
    cur = conn.cursor()

    resolved: list[EntryResolution] = []
    unresolved: list[dict] = []
    totals: dict[str, float] = defaultdict(float)

    for entry in diary.entries:
        food_row = cur.execute(
            "SELECT food_code, food_name FROM foods WHERE food_code = ?",
            (entry.food_code,),
        ).fetchone()

        if food_row is None:
            unresolved.append({
                "food_code": entry.food_code, "quantity": entry.quantity,
                "unit": entry.unit, "error": "food_code not found in database",
            })
            continue

        try:
            grams = to_grams(entry.food_code, entry.quantity, entry.unit)
        except PortionConversionError as e:
            unresolved.append({
                "food_code": entry.food_code, "quantity": entry.quantity,
                "unit": entry.unit, "error": str(e),
            })
            continue

        resolved.append(EntryResolution(
            food_code=food_row["food_code"], food_name=food_row["food_name"],
            quantity=entry.quantity, unit=entry.unit, grams=grams, meal=entry.meal,
        ))

        # nutrient values in the DB are per 100g edible portion, RAW — see
        # cooking_yield.py for why Cereals & Grains / Legumes & Pulses get adjusted
        # here before scaling by the diary's (cooked) quantity.
        scale = grams / 100.0
        nutrient_rows = cur.execute(
            """
            SELECT fn.nutrient_code, fn.value, f.food_group
            FROM food_nutrients fn JOIN foods f ON f.food_code = fn.food_code
            WHERE fn.food_code = ?
            """,
            (entry.food_code,),
        ).fetchall()
        for nrow in nutrient_rows:
            value = adjust_value(nrow["value"], nrow["food_group"])
            totals[nrow["nutrient_code"]] += value * scale

    # attach names/units from the dictionary
    nutrient_totals: list[NutrientTotal] = []
    if totals:
        placeholders = ",".join("?" * len(totals))
        dict_rows = cur.execute(
            f"SELECT nutrient_code, nutrient_name, unit FROM nutrient_dictionary "
            f"WHERE nutrient_code IN ({placeholders})",
            list(totals.keys()),
        ).fetchall()
        dict_map = {r["nutrient_code"]: (r["nutrient_name"], r["unit"]) for r in dict_rows}
        for code, value in sorted(totals.items()):
            name, unit = dict_map.get(code, (None, None))
            nutrient_totals.append(NutrientTotal(
                nutrient_code=code, nutrient_name=name, unit=unit,
                total_value=round(value, 4),
            ))

    conn.close()
    return IntakeResult(
        resolved_entries=resolved,
        nutrient_totals=nutrient_totals,
        unresolved_entries=unresolved,
    )


def get_nutrient_total(intake: IntakeResult, nutrient_code: str) -> float | None:
    """Convenience accessor used by the deficiency analysis module (Phase 3)."""
    for nt in intake.nutrient_totals:
        if nt.nutrient_code == nutrient_code:
            return nt.total_value
    return None


def search_foods(query: str = "", food_group: str | None = None, limit: int = 50) -> list[dict]:
    conn = get_conn()
    sql = "SELECT food_code, food_name, food_group FROM foods WHERE 1=1"
    params: list = []
    if query:
        sql += " AND food_name LIKE ?"
        params.append(f"%{query}%")
    if food_group:
        sql += " AND food_group = ?"
        params.append(food_group)
    sql += " ORDER BY food_name LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
