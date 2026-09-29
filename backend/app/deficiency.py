"""
Deficiency and sufficiency analysis module (thesis objective 3).

Ties together: anthropometrics, DRI lookup, nutrient-code canonicalization, and
the disease-specific nutrition goals table, into one report per profile+diary.
"""
import math
import re

from .anthropometrics import full_anthropometrics, calc_bmr, calc_tee, parse_factor_range
from .conditions import EXTRA_CONDITIONS
from .db import get_conn
from .dri_lookup import parse_age_range_years, lookup_vitamin, lookup_mineral, lookup_protein, lookup_energy
from .nutrient_mapping import CANONICAL_NUTRIENTS, MACRO_CODES, sum_aliases
from .profile import UserProfile
from .schemas import IntakeResult, NutrientStatus, DeficiencyReport, MacroStatus


def _to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _age_category(age: float) -> str:
    if age < 1:
        return "Infant (<1 y)"
    if age < 5:
        return "Pre-school child (1-4 y)"
    if age < 18:
        return "School child / adolescent (5-17 y)"
    return "Adult" if age < 60 else "Older adult (60+ y)"


def _pct_range(text) -> tuple[float, float] | None:
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(text or ""))]
    if len(nums) >= 2:
        return nums[0], nums[1]
    return None


def _age_row(conn, table: str, profile: UserProfile):
    """DRI row by age only (macro tables have no sex split; labels mix 'year'/'years')."""
    age = math.floor(profile.age_years)
    for row in conn.execute(f"SELECT * FROM {table}"):
        label = re.sub(r"years?", "years", row["age_group"] or "", flags=re.I)
        rng = parse_age_range_years(label)
        if rng and rng[0] <= age <= rng[1]:
            return dict(row)
    return None


def _range_status(pct: float | None, rng, label: str):
    if pct is None:
        return "No reference available", "Energy intake is 0, so % of energy cannot be calculated."
    if rng is None:
        return "No reference available", f"No numeric {label} reference range for this age."
    lo, hi = rng
    if pct < lo:
        return "Low", f"{pct:.0f}% of energy is below the {lo:.0f}-{hi:.0f}% range."
    if pct > hi:
        return "High", f"{pct:.0f}% of energy is above the {lo:.0f}-{hi:.0f}% range."
    return "Adequate", f"{pct:.0f}% of energy is within the {lo:.0f}-{hi:.0f}% range."


def _macro_block(conn, profile, intake, energy_block, protein_block):
    """Energy, protein, carbohydrate, fat, fibre - the macro rows of the nutritionist questionnaire."""
    e_kcal = energy_block["intake_kcal"] if energy_block else sum_aliases(intake.nutrient_totals, [MACRO_CODES["Energy"]])
    prot = sum_aliases(intake.nutrient_totals, [MACRO_CODES["Protein"]])
    carb = sum_aliases(intake.nutrient_totals, [MACRO_CODES["Carbohydrate"]])
    fat = sum_aliases(intake.nutrient_totals, [MACRO_CODES["Total Fat"]])
    fibre = sum_aliases(intake.nutrient_totals, [MACRO_CODES["Total Dietary Fibre"]])
    pct = lambda g, k: round(g * k / e_kcal * 100, 1) if e_kcal else None

    carb_row = _age_row(conn, "dri_carbs_fibre", profile)
    fat_row = _age_row(conn, "dri_fat_fatty_acids", profile)
    carb_rng = _pct_range(carb_row["total_carb_pct_e"]) if carb_row else None
    fat_rng = _pct_range(fat_row["total_fat_pct_e"]) if fat_row else None
    prot_rng = (10.0, 35.0)  # AMDR fallback - no % energy range for protein in the DRI file

    out = []
    if energy_block:
        ar = energy_block.get("dri_ar_kcal_day")
        out.append(MacroStatus(nutrient="Energy", unit="kcal", intake=e_kcal,
                               reference=f"AR {ar} kcal/day" if ar else None, status=energy_block["status"]))
    out.append(MacroStatus(
        nutrient="Protein", unit="g", intake=prot, energy_pct=pct(prot, 4),
        reference=f"RDA {protein_block['rda_total_g_day']} g/day" if protein_block and protein_block.get("rda_total_g_day") else None,
        status=protein_block["status"] if protein_block else "No reference available"))
    s, n = _range_status(pct(carb, 4), carb_rng, "carbohydrate")
    out.append(MacroStatus(nutrient="Carbohydrate", unit="g", intake=carb, energy_pct=pct(carb, 4),
                           reference=f"{carb_rng[0]:.0f}-{carb_rng[1]:.0f}% of energy" if carb_rng else None, status=s, note=n))
    s, n = _range_status(pct(fat, 9), fat_rng, "fat")
    out.append(MacroStatus(nutrient="Total fat", unit="g", intake=fat, energy_pct=pct(fat, 9),
                           reference=f"{fat_rng[0]:.0f}-{fat_rng[1]:.0f}% of energy" if fat_rng else None, status=s, note=n))
    fib_ai = _to_float(carb_row["dietary_fibre_g_day"]) if carb_row else None
    out.append(MacroStatus(
        nutrient="Dietary fibre", unit="g", intake=fibre, reference=f"AI {fib_ai} g/day" if fib_ai else None,
        status=("No reference available" if fib_ai is None else "Deficient" if fibre < fib_ai else "Adequate")))

    # Overall nutrient balance (macro distribution): protein/carb/fat % energy inside their ranges
    issues = []
    for m in out:
        if m.nutrient in ("Protein", "Carbohydrate", "Total fat") and m.energy_pct is not None:
            rng = prot_rng if m.nutrient == "Protein" else carb_rng if m.nutrient == "Carbohydrate" else fat_rng
            if rng and not (rng[0] <= m.energy_pct <= rng[1]):
                issues.append(f"{m.nutrient}: {m.energy_pct}% of energy (range {rng[0]:.0f}-{rng[1]:.0f}%)")
    if energy_block and energy_block["status"] == "Deficient":
        issues.append("Energy below requirement")
    if fib_ai and fibre < fib_ai:
        issues.append("Fibre below adequate intake")
    balance = {"verdict": "Satisfactory" if not issues else "Needs review", "issues": issues,
               "note": "Macro balance uses general age-based ranges; condition-specific targets "
                       "(e.g. low-carbohydrate plans) may intentionally sit outside them."}
    return out, balance


def _classify(intake_value: float, ar, rda, ul, ai_ri=None, ceiling: bool = False) -> tuple[str, str | None]:
    """
    ceiling=True flips the interpretation for nutrients (currently just Sodium) whose
    DRI figure is a recommended maximum rather than a sufficiency floor — i.e. "low
    salt" framing, matching how it's used across the disease_nutrition_goals table.
    For those, above the reference is the problem, not below it.
    """
    ar_f, rda_f, ul_f = _to_float(ar), _to_float(rda), _to_float(ul)
    ai_f = _to_float(ai_ri)
    reference = rda_f if rda_f is not None else (ar_f if ar_f is not None else ai_f)
    ref_label = "RDA" if rda_f is not None else ("AR" if ar_f is not None else "AI")
    if reference is None:
        return "No reference available", "No numeric AR/RDA/AI found for this profile/nutrient combination."

    if ceiling:
        if intake_value > reference:
            return "Excess", f"Above the recommended maximum {ref_label} ({reference})."
        return "Adequate", f"At or below the recommended maximum {ref_label} ({reference})."

    if ul_f is not None and intake_value > ul_f:
        return "Excess", f"Above the tolerable upper intake level ({ul_f})."
    if intake_value < reference:
        return "Deficient", f"Below the {ref_label} ({reference})."
    return "Adequate", f"Meets the {ref_label} ({reference})."


def analyze(profile: UserProfile, intake: IntakeResult) -> DeficiencyReport:
    conn = get_conn()
    data_gaps: list[str] = []

    anthro = full_anthropometrics(profile)
    if anthro.get("is_pediatric"):
        data_gaps.append(
            "Patient is under 18 — BMI classification and ideal body weight use "
            "adult-only standards and are not shown for this profile. Accurate pediatric "
            "anthropometrics would need age/sex-specific growth-chart data not present "
            "in the current source files."
        )

    # --- Energy: DRI table + Harris-Benedict cross-check ---
    energy_row = lookup_energy(conn, profile)
    energy_intake = sum_aliases(intake.nutrient_totals, [MACRO_CODES["Energy"]])
    energy_block = None
    if energy_row:
        ar_energy = energy_row.get("ar_energy_kcal_day")
        bmr = anthro["bmr_kcal_day"]
        tee = None
        if profile.occupation_activity_level:
            factor_row = conn.execute(
                "SELECT factor_range FROM activity_factors WHERE activity_level = ?",
                (profile.occupation_activity_level,),
            ).fetchone()
            if factor_row:
                _, _, mid_factor = parse_factor_range(factor_row["factor_range"])
                tee = calc_tee(bmr, mid_factor)
        energy_block = {
            "intake_kcal": energy_intake,
            "dri_ar_kcal_day": ar_energy,
            "harris_benedict_bmr_kcal_day": bmr,
            "harris_benedict_tee_kcal_day": tee,
            "status": (
                "Deficient" if ar_energy and energy_intake < ar_energy
                else "Adequate" if ar_energy else "No reference available"
            ),
        }
    else:
        data_gaps.append(
            "No matching DRI energy row found for this age/sex/physiological-status/PAL "
            "combination — energy adequacy could not be assessed."
        )

    # --- Protein ---
    protein_row = lookup_protein(conn, profile)
    protein_intake = sum_aliases(intake.nutrient_totals, [MACRO_CODES["Protein"]])
    protein_block = None
    if protein_row:
        rda_per_kg = protein_row.get("rda_g_per_kg_bw_day")
        rda_total = round(rda_per_kg * profile.weight_kg, 1) if rda_per_kg else None
        protein_block = {
            "intake_g": protein_intake,
            "rda_g_per_kg_bw_day": rda_per_kg,
            "rda_total_g_day": rda_total,
            "status": (
                "Deficient" if rda_total and protein_intake < rda_total
                else "Adequate" if rda_total else "No reference available"
            ),
        }
    else:
        data_gaps.append(
            "No matching DRI protein row found for this profile — protein adequacy "
            "could not be assessed against a numeric target (shown as raw intake only)."
        )

    # --- Vitamins & minerals ---
    # Thiamine and Niacin in the DRI sheet are stored as per-kcal factors, not absolute
    # mg/day (per the sheet's own footnote: "multiply by individual energy AR/RDA from
    # the Energy sheet to get mg or NE/day"). Comparing the raw factor against intake
    # directly would be comparing the wrong units entirely (e.g. 0.0004 vs an intake in
    # mg) — convert using this profile's own energy AR before classifying.
    energy_ar_kcal = energy_row.get("ar_energy_kcal_day") if energy_row else None
    PER_KCAL_NUTRIENTS = {"Thiamine (B1)", "Niacin (B3)"}

    # Sodium's DRI row is stored in g/day while food composition data is in mg — the
    # only unit mismatch among the mapped nutrients (verified: everything else is
    # already mg-to-mg or µg-to-µg). Also, Sodium's AI functions as a recommended
    # MAXIMUM (matches "low salt" appearing across disease_nutrition_goals), not a
    # sufficiency floor like other AI-referenced nutrients — so it's treated as a
    # ceiling in _classify rather than the usual floor.
    UNIT_SCALE_TO_MG = {"Sodium": 1000}
    CEILING_NUTRIENTS = {"Sodium"}

    nutrient_status: list[NutrientStatus] = []
    for canon_name, (table, dri_name, codes, unit) in CANONICAL_NUTRIENTS.items():
        intake_value = sum_aliases(intake.nutrient_totals, codes)
        row = (
            lookup_vitamin(conn, dri_name, profile) if table == "dri_vitamins"
            else lookup_mineral(conn, dri_name, profile)
        )
        if row is None:
            nutrient_status.append(NutrientStatus(
                nutrient=canon_name, unit=unit, intake=intake_value,
                status="No reference available",
                note="No matching DRI row for this age/sex/physiological-status.",
            ))
            data_gaps.append(f"No DRI reference row matched for {canon_name} with this profile.")
            continue
        ar, rda, ul, ai_ri = row.get("ar"), row.get("rda"), row.get("ul"), row.get("ai_ri")

        if canon_name in PER_KCAL_NUTRIENTS:
            if energy_ar_kcal is None:
                nutrient_status.append(NutrientStatus(
                    nutrient=canon_name, unit=unit, intake=intake_value,
                    status="No reference available",
                    note="This nutrient's DRI is a per-kcal factor and needs an energy "
                         "AR to convert to mg/day, but no energy row matched this profile.",
                ))
                continue
            ar_f, rda_f = _to_float(ar), _to_float(rda)
            ar = round(ar_f * energy_ar_kcal, 3) if ar_f is not None else None
            rda = round(rda_f * energy_ar_kcal, 3) if rda_f is not None else None

        if canon_name in UNIT_SCALE_TO_MG:
            scale = UNIT_SCALE_TO_MG[canon_name]
            ar_f, rda_f, ai_f = _to_float(ar), _to_float(rda), _to_float(ai_ri)
            ar = ar_f * scale if ar_f is not None else None
            rda = rda_f * scale if rda_f is not None else None
            ai_ri = ai_f * scale if ai_f is not None else None

        status, note = _classify(intake_value, ar, rda, ul, ai_ri, ceiling=canon_name in CEILING_NUTRIENTS)
        if canon_name in PER_KCAL_NUTRIENTS and note:
            note += f" (converted from a per-kcal DRI factor using this profile's energy AR of {energy_ar_kcal} kcal/day.)"
        nutrient_status.append(NutrientStatus(
            nutrient=canon_name, unit=unit, intake=intake_value,
            ar=_to_float(ar), rda=_to_float(rda), ul=_to_float(ul), ai=_to_float(ai_ri),
            status=status, note=note,
        ))

    # --- Disease-specific nutrition goals (objective 3 tie-in to objective 4) ---
    disease_goals = []
    for disease in profile.diseases:
        row = conn.execute(
            "SELECT disease_condition, nutrition_goal_text FROM disease_nutrition_goals "
            "WHERE disease_condition = ?",
            (disease,),
        ).fetchone()
        if row:
            disease_goals.append(dict(row))
        elif disease in EXTRA_CONDITIONS:
            disease_goals.append({"disease_condition": disease,
                                  "nutrition_goal_text": EXTRA_CONDITIONS[disease]["goal_text"]})
        else:
            data_gaps.append(
                f"Disease condition '{disease}' does not exactly match any entry in "
                f"disease_nutrition_goals — check GET /diseases for valid values."
            )

    macros, balance = _macro_block(conn, profile, intake, energy_block, protein_block)
    conn.close()

    return DeficiencyReport(
        age_category=_age_category(profile.age_years), macronutrients=macros,
        nutrient_balance=balance, entry_breakdown=intake.entry_breakdown,
        anthropometrics=anthro,
        energy_requirement=energy_block,
        protein_requirement=protein_block,
        nutrient_status=nutrient_status,
        disease_nutrition_goals=disease_goals,
        data_gaps=data_gaps,
    )
