"""
Clinical conditions required by the nutritionist accuracy-assessment questionnaire that are
NOT in the source disease_nutrition_goals table (which came from Nutrition_goals.docx).

Each entry has `goal_text` (shown in the report) and `rules` (same schema as
meal_planning.DISEASE_RULES). Thresholds are population-level HEURISTICS for a prototype,
not individual prescriptions — the nutritionist evaluation is exactly where they get checked.
"""

def _copy_rules(**over):
    return dict(over)

EXTRA_CONDITIONS = {
    "Overweight/ Obesity (adult)": {
        "goal_text": "Modest energy deficit\nLow simple sugars / low GI carbohydrate\nHigh fibre\nLean protein\nLow fat",
        "rules": {"energy_target_multiplier": 0.85, "max_gi": 55, "max_fat_g_100g": 15,
                  "fiber_bonus_weight": 2.0, "prefer_protein_groups": True,
                  "unsupported": ["Energy target = DRI AR x 0.85 (~15% deficit) is a heuristic; "
                                  "a dietitian should set the individual deficit"]},
    },
    "Overweight/ Obesity (school child)": {
        "goal_text": "Do NOT restrict energy sharply (growth); reduce energy-dense, high-fat, high-sugar foods\nHigh fibre\nLean protein",
        "rules": {"energy_target_multiplier": 0.95, "max_gi": 55, "max_fat_g_100g": 15,
                  "fiber_bonus_weight": 2.0, "prefer_protein_groups": True,
                  "unsupported": ["Child BMI-for-age needs WHO growth-reference data that is not in the source files"]},
    },
    "Type 2 diabetes mellitus": {
        "goal_text": "Low GI carbohydrate, controlled portions\nLow simple sugars\nHigh fibre\nLow salt\nOmega-6:omega-3 near 3:1",
        "rules": {"max_sodium_mg_100g": 120, "max_gi": 55, "boost_omega3": True,
                  "fiber_bonus_weight": 2.0, "prefer_protein_groups": True,
                  "unsupported": ["No sugar column in source data (approximated via GI)",
                                  "Carbohydrate distribution across meals is not modelled"]},
    },
    "Hypercholesterolemia": {
        "goal_text": "Low saturated fat and cholesterol\nHigh soluble fibre\nOmega-3 rich foods (fish)\nLow salt",
        "rules": {"max_sat_fat_mg_100g": 3000, "max_cholesterol_mg_100g": 150, "max_sodium_mg_100g": 120,
                  "boost_omega3": True, "fiber_bonus_weight": 2.5, "prefer_protein_groups": True,
                  "exclude_name_keywords": ["ghee", "butter", "lard", "cream", "coconut milk"],
                  "unsupported": ["Coconut products are excluded via the saturated-fat cap; a nutritionist "
                                  "may allow small measured amounts"]},
    },
    "Patient within one week after stenting": {
        "goal_text": "Low salt\nLow saturated fat and cholesterol\nOmega-3 rich foods\nHigh fibre\nAvoid alcohol",
        "rules": {"max_sodium_mg_100g": 120, "max_sat_fat_mg_100g": 3000, "max_cholesterol_mg_100g": 150,
                  "boost_omega3": True, "fiber_bonus_weight": 2.0, "prefer_protein_groups": True,
                  "exclude_name_keywords": ["ghee", "butter", "lard", "cream", "alcohol", "beer", "wine", "arrack", "toddy"],
                  "unsupported": ["Vitamin K consistency for patients on warfarin is a clinical instruction, not modelled"]},
    },
    "Irritable bowel syndrome": {
        "goal_text": "Low irritant / low spice diet\nAvoid high-FODMAP triggers (onion, garlic)\nModerate fat\nRegular small meals",
        "rules": {"exclude_food_groups": ["Condiments & Spices"], "max_fat_g_100g": 15,
                  "exclude_name_keywords": ["onion", "garlic", "chilli", "chili"],
                  "unsupported": ["No FODMAP data in source files; onion/garlic exclusion is an approximation"]},
    },
    "Gastritis": {
        "goal_text": "Avoid spicy, acidic, very fatty and irritant foods\nAvoid alcohol, strong tea/coffee",
        "rules": {"exclude_food_groups": ["Condiments & Spices"], "max_fat_g_100g": 15,
                  "exclude_name_keywords": ["chilli", "chili", "pepper", "vinegar", "lime", "lemon", "pickle",
                                            "tamarind", "alcohol", "beer", "wine", "arrack", "toddy", "coffee"],
                  "unsupported": ["Cooking method (fried) and food acidity are not tracked"]},
    },
    "Gluten intolerance": {
        "goal_text": "Gluten free foods",
        "rules": {"exclude_name_keywords": ["wheat", "atta", "maida", "semolina", "rava", "barley", "rye"],
                  "unsupported": ["Not a certified gluten-free guarantee (no cross-contamination data)"]},
    },
    "Underweight (adult)": {
        "goal_text": "Energy surplus\nEnergy- and nutrient-dense foods\nHigher protein",
        "rules": {"energy_target_multiplier": 1.15, "protein_target_multiplier": 1.2, "prefer_protein_groups": True,
                  "unsupported": ["Energy target = DRI AR x 1.15 is a heuristic"]},
    },
    "Underweight (pre-school child)": {
        "goal_text": "Energy surplus for catch-up growth\nEnergy- and nutrient-dense foods\nHigher protein, frequent meals",
        "rules": {"energy_target_multiplier": 1.2, "protein_target_multiplier": 1.2, "prefer_protein_groups": True,
                  "unsupported": ["Weight-for-age / catch-up targets need WHO growth-reference data (not in source files)"]},
    },
    "Tube feeding": {
        "goal_text": "Nutrition delivered as enteral formula / blenderised feed under clinical supervision",
        "rules": {"tube_feeding": True, "unsupported": []},
    },
}
TUBE_FEEDING_DISEASE = "Tube feeding"
