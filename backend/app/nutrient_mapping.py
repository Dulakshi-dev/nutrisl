"""
KNOWN DATA-QUALITY GAP (flagging explicitly, not silently working around it):

Your FoodCompositionData_GI.xlsx uses different header codes for the same nutrient
in different food-group sheets — e.g. Thiamine appears as both 'THIA' and 'THIAMINE',
Vitamin A as both 'VIT-A' and 'VITA', Vitamin D as 'ERGCAL', 'VIT-D(ERGCAL)', and
'VITDEQ' depending on the sheet. This is presumably an artifact of how the source
Excel was assembled from multiple MRI table exports. It doesn't corrupt any single
food's data — each food only ever has one of the aliases — but it DOES mean that if
you sum "THIA" alone across a mixed diary you'll silently miss Thiamine from foods
that came from a sheet using "THIAMINE" instead.

This module maps every DRI-comparable nutrient to the set of raw codes that
represent it, so the deficiency engine sums across all known aliases. Recommended
follow-up: clean the source headers so Phase 1 ingestion produces single codes
directly — this mapping is a working fix, not a replacement for that.

Also flagging: Vitamin B12 does not appear anywhere in the food composition data
(checked — no code or name matches). If DRI comparison for B12 matters for your
evaluation, that nutrient will need to be sourced and added separately; it is
NOT included below because there's nothing to map it to.
"""

# canonical_name -> (dri_table, dri_row_name, [aliased food_nutrient codes], unit)
CANONICAL_NUTRIENTS = {
    "Vitamin A":        ("dri_vitamins", "Vitamin A",        ["VIT-A", "VITA"], "µg"),
    "Vitamin C":        ("dri_vitamins", "Vitamin C",        ["VITC"], "mg"),
    # NOTE: 'VIT-D(ERGCAL)' was already merged into 'ERGCAL' at ingestion (build_db.py's
    # NUTRIENT_ALIASES). Deliberately NOT summing in 'VITDEQ' (Vitamin D Equivalent) or
    # 'CHOCAL' (Cholecalciferol/D3) here — it's unclear from the source data whether those
    # are additive with ERGCAL or already overlap with it for a given food, and summing
    # them blind risks silently double-counting. They're still in nutrient_dictionary and
    # queryable per-food; just excluded from this DRI-compared total until clarified.
    "Vitamin D":        ("dri_vitamins", "Vitamin D",        ["ERGCAL"], "µg"),
    "Vitamin E":        ("dri_vitamins", "Vitamin E",        ["VIT-E", "VITE"], "mg"),
    "Vitamin K":        ("dri_vitamins", "Vitamin K",        ["VIT-K", "VITK1"], "µg"),
    "Thiamine (B1)":    ("dri_vitamins", "Thiamine (B1)",    ["THIA", "THIAMINE"], "mg"),
    "Riboflavin (B2)":  ("dri_vitamins", "Riboflavin (B2)",  ["RIBF", "RIBOFLAVIN"], "mg"),
    "Niacin (B3)":      ("dri_vitamins", "Niacin (B3)",      ["NIA", "NIACIN"], "mg"),
    "Vitamin B6":       ("dri_vitamins", "Vitamin B6",       ["VITB6C"], "mg"),
    "Folate (B9)":      ("dri_vitamins", "Folate",           ["FOLATE-SUM", "FOLSUM"], "µg"),  # DB row name is just "Folate"
    "Calcium":          ("dri_minerals", "Calcium",          ["CA"], "mg"),
    "Iron":             ("dri_minerals", "Iron",             ["FE"], "mg"),
    "Zinc":             ("dri_minerals", "Zinc",             ["ZN"], "mg"),
    "Magnesium":        ("dri_minerals", "Magnesium",        ["MG"], "mg"),
    "Phosphorus":       ("dri_minerals", "Phosphorus",       ["P"], "mg"),
    "Potassium":        ("dri_minerals", "Potassium",        ["K"], "mg"),
    "Sodium":           ("dri_minerals", "Sodium",           ["NA"], "mg"),
    "Selenium":         ("dri_minerals", "Selenium",         ["SE"], "µg"),
}

# nutrient codes not tied to a DRI vitamin/mineral row, but still useful in the report
MACRO_CODES = {
    "Energy": "ENERC",
    "Protein": "PROTCNT",
    "Total Fat": "FATCE",
    "Total Dietary Fibre": "FIBTG",
    "Carbohydrate": "CHOAVLDF",
}


def sum_aliases(nutrient_totals: list, codes: list[str]) -> float:
    """nutrient_totals is IntakeResult.nutrient_totals; sums whichever aliases are present."""
    total = 0.0
    for nt in nutrient_totals:
        if nt.nutrient_code in codes:
            total += nt.total_value
    return round(total, 4)
