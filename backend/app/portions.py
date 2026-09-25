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
