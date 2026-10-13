"""
Portion-size conversion.

IMPORTANT / KNOWN GAP:
Your thesis proposal (4.2) calls for portion sizes to be converted to grams using
"standard Sri Lankan portion size references." None of the three files you gave me
contain that reference table (it's a separate thing — e.g. household-measure-to-gram
tables published alongside the FBDG or by the Dept. of Nutrition/MRI). What's below
is a generic, commonly-used approximation set (a "cup" ~240ml, "tbsp" ~15ml, etc.)
so the calculator is functional end-to-end right now — but it is NOT the Sri Lankan
reference your objective 2 specifies, and using it as-is will introduce real error,
especially for solid/lumpy foods (rice, curries) where volume-to-weight varies a lot
by food. Before your evaluation phase, swap GENERIC_VOLUME_TO_ML and add
per-food-group gram weights (e.g. from the FBDG household measures appendix) into
PORTION_OVERRIDES below — the calculator code doesn't need to change, just this file.
"""

# Generic ml equivalents for common household volume units (approximate, not SL-specific)
GENERIC_VOLUME_TO_ML = {
    "cup": 240.0,
    "tbsp": 15.0,
    "tsp": 5.0,
    "ml": 1.0,
    "l": 1000.0,
}

# Per-food, per-unit gram overrides — populate this as you get real reference data,
# e.g. PORTION_OVERRIDES[("SLA010", "piece")] = 25.0  # one idli = 25g
PORTION_OVERRIDES: dict[tuple[str, str], float] = {}

# --- Nutritionist-supplied household measures (grams per ONE unit) -----------------
# Applied per food code so the generic 240 ml / 15 ml / 1 g-per-ml fallback (which
# overestimates solid foods) is never used for these foods.
#   cooked rice          1 cup  = 140 g (cooked weight)
#   vegetables           1 tbsp = 20 g
#   green leaves         1 tbsp = 10 g
#   scraped coconut      1 tbsp = 10 g
# Rice entries are COOKED weight; cooking_yield.py then divides the raw-table nutrient
# density by 2.5, so the two corrections stay consistent.

COOKED_RICE_CODES = [f"SLA{n:03d}" for n in range(7, 14)]  # SLA007-SLA013 (not flakes/vermicelli)

GREEN_LEAF_CODES = [
    "SLD001", "SLD002", "SLD003", "SLD012", "SLD022", "SLD025", "SLD030", "SLD034",
    "SLD042", "SLD043", "SLD045", "SLD046", "SLD047", "SLD048", "SLD052", "SLD056",
    "SLD057", "SLD061", "SLD063", "SLD064", "SLD070", "SLD074", "SLD076", "SLD080",
    "SLD081", "SLD086",
]
_LEAF_SET = set(GREEN_LEAF_CODES)
# Every other food in the "Vegetables" group (SLD001-SLD089) counts as a plain vegetable.
VEGETABLE_CODES = [f"SLD{n:03d}" for n in range(1, 90) if f"SLD{n:03d}" not in _LEAF_SET]

for _c in COOKED_RICE_CODES:
    PORTION_OVERRIDES[(_c, "cup")] = 140.0
for _c in VEGETABLE_CODES:
    PORTION_OVERRIDES[(_c, "tbsp")] = 20.0
for _c in GREEN_LEAF_CODES:
    PORTION_OVERRIDES[(_c, "tbsp")] = 10.0
PORTION_OVERRIDES[("SLI006", "tbsp")] = 10.0  # coconut, kernel, fresh, scraped

# Assumed density (g/ml) for volume->weight conversion when no override exists.
# 1.0 is a reasonable default for watery liquids; wrong for rice, oils, etc.
DEFAULT_DENSITY_G_PER_ML = 1.0


class PortionConversionError(Exception):
    pass


def to_grams(food_code: str, quantity: float, unit: str) -> float:
    """Convert a diary entry (food_code, quantity, unit) to grams."""
    unit = unit.strip().lower()

    if unit in ("g", "gram", "grams"):
        return quantity
    if unit in ("kg", "kilogram", "kilograms"):
        return quantity * 1000.0

    override = PORTION_OVERRIDES.get((food_code, unit))
    if override is not None:
        return quantity * override

    if unit in GENERIC_VOLUME_TO_ML:
        ml = quantity * GENERIC_VOLUME_TO_ML[unit]
        return ml * DEFAULT_DENSITY_G_PER_ML

    raise PortionConversionError(
        f"No gram conversion available for unit '{unit}' on food '{food_code}'. "
        f"Enter grams directly, or add a PORTION_OVERRIDES entry for this food+unit."
    )