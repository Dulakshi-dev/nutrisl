"""
Cooking-yield adjustment — added following clinical validation feedback.

The food composition data in this database is RAW/uncooked, as published in the
source Sri Lanka Food Composition Table. Food diary entries, however, record the
weight of food AS EATEN — i.e. cooked. Cereals and legumes absorb substantial water
during cooking (rice/lentils roughly 2-3x in weight), which dilutes nutrient density
per gram. Applying raw-table values directly to a cooked-weight quantity therefore
overestimates every nutrient proportionally, energy included — this is exactly what
the reviewing nutritionist flagged (energy values reading far too high).

Her recommended fix: divide nutrient values for Cereals & Grains and Legumes & Pulses
by 2.5 to approximate their cooked-state density, applied uniformly across every
nutrient for those two food groups (not just energy), since the underlying cause —
water dilution — affects all nutrients proportionally, not energy alone.

LIMITATIONS, stated plainly rather than hidden:
- This is a blanket approximation shared across both food groups and every food
  within them. Real cooking yield varies by specific food (plain rice vs. red lentils
  vs. parboiled rice vs. chickpeas all absorb water differently) and by cooking method
  (boiled vs. steamed vs. pressure-cooked). 2.5 is a reasonable single estimate, not a
  food-specific figure.
- A more accurate long-term fix would be to source the Sri Lanka Food Composition
  Table's own COOKED-food entries where they exist, rather than applying a flat
  divisor to raw entries — worth pursuing if time allows before final submission.
- This divisor is applied identically everywhere raw nutrient values are read
  (the intake calculator, meal-plan food scoring, and the single-food lookup
  endpoint) so the system is internally consistent; it is never applied twice to
  the same value.
"""

COOKED_YIELD_DIVISOR = 2.5

RAW_FOOD_GROUPS_NEEDING_YIELD_ADJUSTMENT = {"Cereals & Grains", "Legumes & Pulses"}


def adjust_value(value: float, food_group: str) -> float:
    """Apply the cooking-yield divisor if this food group's data is raw/uncooked."""
    if food_group in RAW_FOOD_GROUPS_NEEDING_YIELD_ADJUSTMENT:
        return value / COOKED_YIELD_DIVISOR
    return value
