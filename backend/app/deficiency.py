"""
Deficiency and sufficiency analysis module (thesis objective 3).

Ties together: anthropometrics, DRI lookup, nutrient-code canonicalization, and
the disease-specific nutrition goals table, into one report per profile+diary.
"""
from .anthropometrics import full_anthropometrics, calc_bmr, calc_tee, parse_factor_range
from .db import get_conn
from .dri_lookup import lookup_vitamin, lookup_mineral, lookup_protein, lookup_energy
from .nutrient_mapping import CANONICAL_NUTRIENTS, MACRO_CODES, sum_aliases
from .profile import UserProfile
from .schemas import IntakeResult, NutrientStatus, DeficiencyReport


def _to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


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
        else:
            data_gaps.append(
                f"Disease condition '{disease}' does not exactly match any entry in "
                f"disease_nutrition_goals — check GET /diseases for valid values."
            )

    conn.close()

    return DeficiencyReport(
        anthropometrics=anthro,
        energy_requirement=energy_block,
        protein_requirement=protein_block,
        nutrient_status=nutrient_status,
        disease_nutrition_goals=disease_goals,
        data_gaps=data_gaps,
    )
