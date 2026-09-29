"""
Meal planning module (thesis objective 4).

HONEST SCOPE NOTE — read this before trusting any of DISEASE_RULES below:
Your Nutrition_goals.docx gives each disease as free-text clinical guidance, not
structured data. Turning "Low salt" into "exclude foods over 120mg sodium/100g" is
MY interpretation, not something derivable purely from the data — same for every
threshold below. These are reasonable population-level heuristics for a working
prototype, NOT individualized clinical prescriptions (this matters especially for
kidney disease and pancreatitis, where real target numbers are patient-specific and
should come from a dietitian, not a fixed cutoff). Flag this plainly in your thesis
write-up and treat objective 5's nutritionist validation as the point where these
specific numbers get checked, not treated as ground truth.

Several goal-text items have NO corresponding data field anywhere in your three
source files and are NOT enforced, listed explicitly per-disease in `unsupported`:
amylose:amylopectin ratio, "fried" as a cooking method, "spice/irritant level"
(approximated only via excluding the Condiments & Spices group), simple-sugar
content specifically (no such column exists — approximated via GI where relevant),
and anything requiring amino-acid-level detail (Phenylketonuria) or infant-specific
feeding (Galactocemia in neonates) — those two are refused outright rather than
faked, see PKU_DISEASE / INFANT_ONLY_DISEASE below.
"""
from .calculator import calculate_intake
from .conditions import EXTRA_CONDITIONS, TUBE_FEEDING_DISEASE
from .db import get_conn
from .deficiency import analyze
from .nutrient_mapping import MACRO_CODES
from .profile import UserProfile
from .schemas import DiaryInput, MealPlanItem, MealPlanResult

# ---------------------------------------------------------------------------
# Disease -> operational rules, hand-mapped from the exact goal text (see module
# docstring). "unsupported" lists goal-text items this engine does NOT enforce.
# ---------------------------------------------------------------------------
DISEASE_RULES = {
    "Diabetes mellitus, dyslipidemia, obesity": {
        "max_sodium_mg_100g": 120, "max_gi": 55, "boost_omega3": True,
        "fiber_bonus_weight": 2.0, "prefer_protein_groups": True,
        "unsupported": ["amylose:amylopectin ratio (no starch-structure data)",
                         "'less fried foods' (cooking method not tracked)",
                         "simple sugars specifically (no sugar column; approximated via GI)"],
    },
    "Kidney diseases": {
        "max_sodium_mg_100g": 120, "max_potassium_mg_100g": 200, "max_phosphorus_mg_100g": 100,
        "protein_target_multiplier": 0.9,
        "unsupported": ["exact renal potassium/phosphorus/protein limits are patient-specific "
                         "and should come from a renal dietitian — 200mg/100g and 100mg/100g "
                         "are population heuristics, not a prescribed clinical limit"],
    },
    "Celiac disease": {
        "exclude_name_keywords": ["wheat", "atta", "maida", "semolina", "rava", "barley", "rye"],
        "unsupported": ["not a certified gluten-free guarantee — no allergen/cross-contamination data exists"],
    },
    "Lactose intolerance": {
        "exclude_food_groups": ["Milk & Dairy Products"],
        "keep_name_keywords": ["yog", "curd"],  # exception per the goal text itself
        "unsupported": [],
    },
    "IBD / Crohn's / Colitis": {
        "max_fiber_g_100g": 2, "exclude_food_groups": ["Condiments & Spices"],
        "unsupported": ["'irritant' quality beyond the spice food group isn't tagged in the data"],
    },
    "Constipation": {
        "fiber_bonus_weight": 2.5, "boost_name_keywords": ["tamarind"],
        "unsupported": ["'more water' isn't a food-diary item — advise separately"],
    },
    "Fatty liver/ cirrhosis": {
        "max_fat_g_100g": 5, "carb_penalty_weight": 1.5, "prefer_protein_groups": True,
        "exclude_name_keywords": ["alcohol", "beer", "wine", "arrack", "toddy"],
        "unsupported": [],
    },
    "Severe Burns/ after major surgery": {
        "protein_target_multiplier": 1.5, "prefer_protein_groups": True,
        "unsupported": ["real burn/post-op protein needs vary 1.5-2x normal depending on "
                         "severity — 1.5x is a placeholder, not individualized"],
    },
    "Diabetes + severe burn": {
        "max_sodium_mg_100g": 120, "max_gi": 55, "boost_omega3": True,
        "fiber_bonus_weight": 2.0, "prefer_protein_groups": True,
        "protein_target_multiplier": 1.5,
        "unsupported": ["same combined caveats as Diabetes and Severe Burns entries"],
    },
    "Galactocemia in neonates": {"infant_only": True, "unsupported": []},
    "pancreatitis": {
        "max_fat_g_100g": 5, "fiber_bonus_weight": 2.0, "prefer_protein_groups": True,
        "exclude_name_keywords": ["sausage", "bacon", "duck", "cream", "chocolate", "avocado",
                                    "alcohol", "beer", "wine", "arrack"],
        "unsupported": ["fat-soluble vitamin (A,D,E,K) supplementation is a clinical add-on, "
                         "not something food selection alone can guarantee"],
    },
    "Gallstones/ cholecystectomy": {
        "max_fat_g_100g": 8, "prefer_protein_groups": True, "unsupported": [],
    },
    "Old age": {
        "protein_target_multiplier": 1.15,
        "priority_nutrient_boost": ["Vitamin D", "Calcium", "Zinc", "Iron"],
        "unsupported": ["'vitamin D supplements' is a clinical add-on beyond food selection"],
    },
    "Phenylketone uria": {"pku": True, "unsupported": []},
    "Thalassemia": {
        "avoid_nutrient": "Iron", "priority_nutrient_boost": ["Calcium", "Vitamin D", "Folate (B9)", "Magnesium"],
        "unsupported": ["'avoid vitamin C with iron-rich food' is a meal-pairing/timing rule, "
                         "not a single-food property this engine models"],
    },
    "Ileal resection": {
        "max_fiber_g_100g": 2, "max_fat_g_100g": 8,
        "priority_nutrient_boost": ["Vitamin A", "Vitamin D", "Vitamin E", "Vitamin K"],
        "unsupported": ["Vitamin B12 supplementation — B12 has no data in your food composition file at all"],
    },
}

# Questionnaire conditions (Overweight/obesity, T2DM, hypercholesterolemia, stenting, IBS, ...)
DISEASE_RULES.update({k: v["rules"] for k, v in EXTRA_CONDITIONS.items()})
# Burns: energy demand is raised as well as protein (heuristic, flagged in `unsupported`)
DISEASE_RULES["Severe Burns/ after major surgery"]["energy_target_multiplier"] = 1.2
DISEASE_RULES["Diabetes + severe burn"]["energy_target_multiplier"] = 1.2

PKU_DISEASE = "Phenylketone uria"
INFANT_ONLY_DISEASE = "Galactocemia in neonates"

LEAN_PROTEIN_GROUPS = ["Fish & Aquatic", "Legumes & Pulses", "Milk & Dairy Products", "Eggs, Poultry & Meat"]
ANIMAL_PROTEIN_GROUPS = ["Fish & Aquatic", "Eggs, Poultry & Meat", "Milk & Dairy Products"]
PLANT_PROTEIN_GROUPS = ["Legumes & Pulses"]

# Split for meal-template slotting (separate from LEAN_PROTEIN_GROUPS above, which is
# still used for the general scoring bonus). Lunch/dinner get one slot from EACH list
# so a plan can't end up all-legume for every protein slot in the day — which is what
# actually happened in testing: legumes kept outscoring fish/meat on fiber+GI+deficiency
# signals even though fish/meat weren't filtered out. Splitting the slot forces variety
# regardless of how the scoring leans, rather than tuning scores to fight that tendency.
ANIMAL_PROTEIN_GROUPS = ["Fish & Aquatic", "Eggs, Poultry & Meat"]
PLANT_PROTEIN_GROUPS = ["Legumes & Pulses"]

# Fixed, standard-portion approach (per your decision) — same caveat as portions.py:
# these are generic reasonable serving sizes, not a validated Sri Lankan portion
# reference (which doesn't exist in your source files).
STANDARD_PORTION_G = {
    "Cereals & Grains": 150, "Root Vegetables": 100, "Legumes & Pulses": 75,
    "Vegetables": 75, "Fruits": 100, "Fish & Aquatic": 90, "Milk & Dairy Products": 100,
    "Eggs, Poultry & Meat": 90, "Nuts & Seeds": 30, "Oils & Fats": 5,
    "Condiments & Spices": 5, "Beverages": 150,
}

MEAL_TEMPLATES = {
    "breakfast": [
        {"role": "starch", "groups": ["Cereals & Grains"], "count": 1},
        {"role": "protein", "groups": LEAN_PROTEIN_GROUPS, "count": 1, "optional": True},
    ],
    "lunch": [
        {"role": "starch", "groups": ["Cereals & Grains"], "count": 1},
        # Split rather than pooled: a real Sri Lankan rice-and-curry meal typically has
        # BOTH a fish/meat/dairy curry AND a dhal side, not one or the other. Pooling all
        # 4 protein groups into one slot let legumes dominate every meal in testing (they
        # scored highest on fiber/GI/deficiency signals) — this guarantees variety instead.
        {"role": "animal_protein", "groups": ANIMAL_PROTEIN_GROUPS, "count": 1, "optional": True},
        {"role": "plant_protein", "groups": PLANT_PROTEIN_GROUPS, "count": 1, "optional": True},
        {"role": "vegetable", "groups": ["Vegetables", "Root Vegetables"], "count": 2},
    ],
    "dinner": [
        {"role": "starch", "groups": ["Cereals & Grains"], "count": 1},
        {"role": "animal_protein", "groups": ANIMAL_PROTEIN_GROUPS, "count": 1, "optional": True},
        {"role": "plant_protein", "groups": PLANT_PROTEIN_GROUPS, "count": 1, "optional": True},
        {"role": "vegetable", "groups": ["Vegetables", "Root Vegetables"], "count": 1},
    ],
    # Kept as separate top-level categories (own dict key -> own section in the UI),
    # not nested inside breakfast/lunch/dinner, per explicit request.
    "beverage": [
        {"role": "beverage", "groups": ["Beverages"], "count": 1},
    ],
    "dessert": [
        {"role": "dessert_or_fruit", "groups": ["Fruits", "Nuts & Seeds"], "count": 1},
    ],
}

# Always shown, regardless of which diseases are selected — this is a property of the
# source data itself (build_db.py's ingestion), not something disease rules affect.
RAW_INGREDIENT_DISCLAIMER = (
    "This plan is built entirely from individually-digitized raw ingredients (rice "
    "varieties, curry components, vegetables) — the source Food Composition data "
    "contains NO prepared/composite Sri Lankan dishes (no hoppers, kottu, string "
    "hoppers, pittu, roti, or bread) and only 2 beverage entries (both coconut water; "
    "no tea). What you see for breakfast/lunch/dinner is a legitimate rice-and-curry-style "
    "combination of real ingredients, not a named composed dish — and the Beverage "
    "section reflects the only 2 items that exist in your data, not what most people "
    "would actually drink."
)

OMEGA6_CODES = ["F18D2CN6", "F20D4N6"]
OMEGA3_CODES = ["F18D3N3", "F20D5N3", "F22D5N3", "F22D6N3"]


def sum_energy(intake) -> float:
    return sum(n.total_value for n in intake.nutrient_totals if n.nutrient_code == MACRO_CODES["Energy"])


def sum_protein(intake) -> float:
    return sum(n.total_value for n in intake.nutrient_totals if n.nutrient_code == MACRO_CODES["Protein"])


def _merge_rules(diseases: list[str]) -> dict:
    """Union hard filters (most restrictive wins), sum soft bonuses across selected diseases."""
    merged = {
        "max_sodium_mg_100g": None, "max_potassium_mg_100g": None, "max_phosphorus_mg_100g": None,
        "max_fat_g_100g": None, "max_fiber_g_100g": None, "max_gi": None,
        "max_sat_fat_mg_100g": None, "max_cholesterol_mg_100g": None, "energy_target_multiplier": 1.0,
        "fiber_bonus_weight": 0.0, "carb_penalty_weight": 0.0, "boost_omega3": False,
        "prefer_protein_groups": False, "exclude_food_groups": set(), "exclude_name_keywords": set(),
        "keep_name_keywords": set(), "boost_name_keywords": set(),
        "protein_target_multiplier": 1.0, "priority_nutrient_boost": set(), "avoid_nutrient": None,
        "unsupported": [],
    }
    for d in diseases:
        rules = DISEASE_RULES.get(d)
        if not rules:
            continue
        for cap_key in ("max_sodium_mg_100g", "max_potassium_mg_100g", "max_phosphorus_mg_100g",
                         "max_fat_g_100g", "max_fiber_g_100g", "max_gi",
                         "max_sat_fat_mg_100g", "max_cholesterol_mg_100g"):
            if rules.get(cap_key) is not None:
                cur = merged[cap_key]
                merged[cap_key] = rules[cap_key] if cur is None else min(cur, rules[cap_key])
        merged["energy_target_multiplier"] *= rules.get("energy_target_multiplier", 1.0)
        merged["fiber_bonus_weight"] = max(merged["fiber_bonus_weight"], rules.get("fiber_bonus_weight", 0.0))
        merged["carb_penalty_weight"] = max(merged["carb_penalty_weight"], rules.get("carb_penalty_weight", 0.0))
        merged["boost_omega3"] = merged["boost_omega3"] or rules.get("boost_omega3", False)
        merged["prefer_protein_groups"] = merged["prefer_protein_groups"] or rules.get("prefer_protein_groups", False)
        merged["exclude_food_groups"] |= set(rules.get("exclude_food_groups", []))
        merged["exclude_name_keywords"] |= set(rules.get("exclude_name_keywords", []))
        merged["keep_name_keywords"] |= set(rules.get("keep_name_keywords", []))
        merged["boost_name_keywords"] |= set(rules.get("boost_name_keywords", []))
        # protein multiplier: take the largest adjustment requested (most conservative-safe default)
        merged["protein_target_multiplier"] = max(merged["protein_target_multiplier"], rules.get("protein_target_multiplier", 1.0))
        merged["priority_nutrient_boost"] |= set(rules.get("priority_nutrient_boost", []))
        if rules.get("avoid_nutrient"):
            merged["avoid_nutrient"] = rules["avoid_nutrient"]
        merged["unsupported"].extend(rules.get("unsupported", []))
    return merged


def _name_has_any(name: str, keywords: set) -> bool:
    name_l = name.lower()
    return any(kw.lower() in name_l for kw in keywords)


def _fetch_candidates(conn, profile: UserProfile, rules: dict) -> list[dict]:
    foods = conn.execute("SELECT food_code, food_name, food_group FROM foods").fetchall()
    nutrient_rows = conn.execute("SELECT food_code, nutrient_code, value FROM food_nutrients").fetchall()
    nutrients_by_food: dict[str, dict] = {}
    for r in nutrient_rows:
        nutrients_by_food.setdefault(r["food_code"], {})[r["nutrient_code"]] = r["value"]

    excluded_by_pref = set()
    if profile.dietary_preference == "vegetarian":
        excluded_by_pref |= {"Fish & Aquatic", "Eggs, Poultry & Meat"}
    elif profile.dietary_preference == "vegan":
        excluded_by_pref |= {"Fish & Aquatic", "Eggs, Poultry & Meat", "Milk & Dairy Products"}
    elif profile.dietary_preference == "pescatarian":
        excluded_by_pref |= {"Eggs, Poultry & Meat"}

    dislikes = set(profile.food_dislikes) | set(profile.food_allergies)

    candidates = []
    for f in foods:
        code, name, group = f["food_code"], f["food_name"], f["food_group"]
        nutrients = nutrients_by_food.get(code, {})

        if group in rules["exclude_food_groups"] and not _name_has_any(name, rules["keep_name_keywords"]):
            continue
        if group in excluded_by_pref:
            continue
        if _name_has_any(name, dislikes):
            continue
        if _name_has_any(name, rules["exclude_name_keywords"]):
            continue

        sodium = nutrients.get("NA")
        if rules["max_sodium_mg_100g"] is not None and sodium is not None and sodium > rules["max_sodium_mg_100g"]:
            continue
        potassium = nutrients.get("K")
        if rules["max_potassium_mg_100g"] is not None and potassium is not None and potassium > rules["max_potassium_mg_100g"]:
            continue
        phosphorus = nutrients.get("P")
        if rules["max_phosphorus_mg_100g"] is not None and phosphorus is not None and phosphorus > rules["max_phosphorus_mg_100g"]:
            continue
        fat = nutrients.get(MACRO_CODES["Total Fat"])
        if rules["max_fat_g_100g"] is not None and fat is not None and fat > rules["max_fat_g_100g"]:
            continue
        fiber = nutrients.get(MACRO_CODES["Total Dietary Fibre"])
        if rules["max_fiber_g_100g"] is not None and fiber is not None and fiber > rules["max_fiber_g_100g"]:
            continue

        satfat = nutrients.get("FASAT")
        if rules["max_sat_fat_mg_100g"] is not None and satfat is not None and satfat > rules["max_sat_fat_mg_100g"]:
            continue
        chol = nutrients.get("CHOLC")
        if rules["max_cholesterol_mg_100g"] is not None and chol is not None and chol > rules["max_cholesterol_mg_100g"]:
            continue

        candidates.append({"food_code": code, "food_name": name, "food_group": group, "nutrients": nutrients})
    return candidates


def _score_candidate(cand: dict, deficient_targets: dict, rules: dict, gi_lookup: dict) -> float:
    n = cand["nutrients"]
    score = 0.0

    # 1. Deficiency-closing: reward nutrients this profile is short on, weighted by severity
    for canon_name, info in deficient_targets.items():
        for code in info["codes"]:
            if code in n:
                score += (n[code] / 100.0) * info["severity"] * info.get("weight_multiplier", 1.0)

    # 2. Fiber bonus (constipation/diabetes/pancreatitis 'high fiber' goals)
    if rules["fiber_bonus_weight"] and MACRO_CODES["Total Dietary Fibre"] in n:
        score += n[MACRO_CODES["Total Dietary Fibre"]] * rules["fiber_bonus_weight"]

    # 3. Carb penalty (fatty liver 'low carbohydrate')
    if rules["carb_penalty_weight"] and MACRO_CODES["Carbohydrate"] in n:
        score -= n[MACRO_CODES["Carbohydrate"]] * rules["carb_penalty_weight"] * 0.1

    # 4. Omega 6:3 ratio bonus (target ~3:1) — only meaningful if the food has any omega-3
    if rules["boost_omega3"]:
        o6 = sum(n.get(c, 0) or 0 for c in OMEGA6_CODES)
        o3 = sum(n.get(c, 0) or 0 for c in OMEGA3_CODES)
        if o3 > 0:
            ratio = o6 / o3
            score += max(0.0, 5.0 - abs(ratio - 3.0))  # closer to 3:1 scores higher

    # 5. Lean-protein preference
    if rules["prefer_protein_groups"] and cand["food_group"] in LEAN_PROTEIN_GROUPS:
        score += 3.0

    # 6. Named boosts (e.g. tamarind for constipation)
    if _name_has_any(cand["food_name"], rules["boost_name_keywords"]):
        score += 10.0

    # 7. Avoid-nutrient penalty (Thalassemia: avoid iron-rich foods even though iron may be "deficient")
    if rules["avoid_nutrient"] == "Iron" and "FE" in n:
        score -= n["FE"] * 3.0

    # 8. GI filter/penalty (diabetes 'low GI') — only applied where we found a name match
    if rules["max_gi"] is not None:
        gi = gi_lookup.get(cand["food_code"])
        if gi is not None and gi > rules["max_gi"]:
            score -= 20.0  # strong penalty rather than hard exclude (coverage is partial, see notes)

    return score


def _build_gi_lookup(conn, candidates: list[dict]) -> dict:
    """Best-effort name match between the 331 foods and the 2,489-row GI/GL reference
    (they aren't linked by any shared code). Coverage will be partial — this is a
    documented limitation, not treated as authoritative."""
    gi_rows = conn.execute("SELECT item_description, gi_glucose100 FROM gi_gl_reference").fetchall()
    gi_index = [(r["item_description"].lower(), r["gi_glucose100"]) for r in gi_rows if r["gi_glucose100"] is not None]
    lookup = {}
    for c in candidates:
        name_l = c["food_name"].lower()
        best = None
        for desc, gi in gi_index:
            if desc in name_l or name_l in desc:
                best = gi
                break
        if best is not None:
            lookup[c["food_code"]] = best
    return lookup


def generate_meal_plan(profile: UserProfile, diary: DiaryInput) -> MealPlanResult:
    if PKU_DISEASE in profile.diseases:
        return MealPlanResult(
            generated=False,
            reason="Phenylketonuria management requires phenylalanine-exchange food tables "
                   "(amino-acid-level data) that don't exist anywhere in your three source "
                   "files. Guessing at 'low protein' as a stand-in would be a genuine safety "
                   "risk, not just an accuracy gap — this needs a metabolic dietitian's "
                   "phe-exchange list, not this engine.",
            meals={}, items=[], validation=None, limitations=[],
        )
    if INFANT_ONLY_DISEASE in profile.diseases:
        return MealPlanResult(
            generated=False,
            reason="Galactocemia in neonates concerns infant feeding (breastmilk/formula "
                   "substitution), which this system's adult/child solid-food database and "
                   "DRI framework cannot represent. Needs a neonatal metabolic dietitian, not "
                   "a solid-food meal plan.",
            meals={}, items=[], validation=None, limitations=[],
        )

    if TUBE_FEEDING_DISEASE in profile.diseases:
        return MealPlanResult(
            generated=False,
            reason="Tube feeding is delivered as enteral formula or a blenderised feed prescribed by a "
                   "clinician (volume, osmolarity and viscosity matter). A solid-food rice-and-curry plan "
                   "would be unsafe, so none is generated. Use 'Analyze intake' to check what the feed "
                   "provides (enter it as diary items) against the patient's requirements.",
            meals={}, items=[], validation=None, limitations=[],
        )

    conn = get_conn()
    rules = _merge_rules(profile.diseases)

    # Use the existing Phase 2/3 engine to find out what this profile is short on.
    intake = calculate_intake(diary)
    deficiency_report = analyze(profile, intake)

    deficient_targets = {}
    from .nutrient_mapping import CANONICAL_NUTRIENTS
    for ns in deficiency_report.nutrient_status:
        if ns.status != "Deficient":
            continue
        target = ns.rda or ns.ar or ns.ai
        if not target:
            continue
        severity = max(0.0, min(1.0, 1 - (ns.intake / target)))
        codes = CANONICAL_NUTRIENTS.get(ns.nutrient, (None, None, [], None))[2]
        weight_mult = 3.0 if ns.nutrient in rules["priority_nutrient_boost"] else 1.0
        deficient_targets[ns.nutrient] = {"codes": codes, "severity": severity, "weight_multiplier": weight_mult}
    # priority_nutrient_boost nutrients also get boosted even if not currently deficient
    # (e.g. Old age -> Vitamin D/Calcium/Zinc/Iron regardless of this diary's measured status)
    for canon_name in rules["priority_nutrient_boost"]:
        if canon_name not in deficient_targets:
            codes = CANONICAL_NUTRIENTS.get(canon_name, (None, None, [], None))[2]
            deficient_targets[canon_name] = {"codes": codes, "severity": 0.5, "weight_multiplier": 3.0}

    candidates = _fetch_candidates(conn, profile, rules)
    gi_lookup = _build_gi_lookup(conn, candidates) if rules["max_gi"] is not None else {}

    used_codes: set[str] = set()
    meals: dict[str, list[MealPlanItem]] = {}
    all_items: list[MealPlanItem] = []

    for meal_name, slots in MEAL_TEMPLATES.items():
        meal_items = []
        for slot in slots:
            eligible = [c for c in candidates if c["food_group"] in slot["groups"] and c["food_code"] not in used_codes]
            if not eligible:
                continue
            scored = sorted(eligible, key=lambda c: _score_candidate(c, deficient_targets, rules, gi_lookup), reverse=True)
            for pick in scored[: slot["count"]]:
                used_codes.add(pick["food_code"])
                grams = STANDARD_PORTION_G.get(pick["food_group"], 100)
                item = MealPlanItem(
                    meal=meal_name, role=slot["role"], food_code=pick["food_code"],
                    food_name=pick["food_name"], food_group=pick["food_group"], grams=grams,
                )
                meal_items.append(item)
                all_items.append(item)
        meals[meal_name] = meal_items

    def _run(items):
        d = DiaryInput(entries=[
            {"food_code": it.food_code, "quantity": it.grams, "unit": "g", "meal": it.meal} for it in items
        ])
        return calculate_intake(d)

    # Portion scaling: standard portions are adult-sized, so scale them to this patient's energy
    # target (DRI energy AR x condition multiplier). Fixes child/elderly portions being too large
    # and underweight/obesity plans not reflecting their energy goal.
    target_kcal = None
    scale = 1.0
    ar = (deficiency_report.energy_requirement or {}).get("dri_ar_kcal_day")
    if ar:
        target_kcal = round(float(ar) * rules["energy_target_multiplier"])
        plan_kcal = sum_energy(_run(all_items))
        if plan_kcal > 0:
            scale = max(0.4, min(2.0, target_kcal / plan_kcal))
            for it in all_items:
                it.grams = max(5.0, round(it.grams * scale / 5) * 5)
        # protein top-up on protein-role items if still under the (condition-adjusted) target
        prot_row = deficiency_report.protein_requirement or {}
        prot_target = (prot_row.get("rda_total_g_day") or 0) * rules["protein_target_multiplier"]
        prot_now = sum_protein(_run(all_items))
        if prot_target and prot_now < 0.95 * prot_target:
            boost = min(1.6, prot_target / max(prot_now, 1e-6))
            for it in all_items:
                if "protein" in it.role:
                    it.grams = round(it.grams * boost / 5) * 5

    # Closed-loop validation: run the generated plan back through the same calculator+analyzer
    validation_intake = _run(all_items)
    validation_report = analyze(profile, validation_intake)

    limitations = list(dict.fromkeys(rules["unsupported"]))  # de-dupe, preserve order
    limitations.insert(0, RAW_INGREDIENT_DISCLAIMER)
    if target_kcal:
        limitations.insert(1, (
            f"Portions were scaled (x{scale:.2f}) so the plan supplies about {target_kcal} kcal/day "
            f"(DRI energy requirement adjusted for the selected condition). Portion weights are "
            f"generic estimates, not validated Sri Lankan household measures."
        ))
    if rules["max_gi"] is not None:
        limitations.append(
            f"GI/GL reference matched by food name only (not linked by code) — "
            f"{len(gi_lookup)}/{len(candidates)} candidate foods had a GI match; "
            f"foods without a match were not GI-filtered."
        )
    if any(f["max_potassium_mg_100g"] or f["max_phosphorus_mg_100g"] for f in [rules]):
        pass  # already covered by the Kidney entry's unsupported note

    conn.close()
    return MealPlanResult(
        generated=True, reason=None, meals=meals, items=all_items,
        validation=validation_report, limitations=limitations,
        target_energy_kcal=target_kcal, portion_scale_factor=round(scale, 2),
    )
