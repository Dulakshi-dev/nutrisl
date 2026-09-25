"""
Anthropometric calculations per the thesis's nutrition-goals reference document.

Formulas and cutoffs below are transcribed directly from the "Outcomes" section of
Nutrition_goals.docx and the classification_cutoffs table (ingested from its BMI1 /
Waist2 / Waist:hip ratio3 rows) — nothing here is invented.
"""
import re
from .profile import UserProfile


def calc_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 2)


def classify_bmi(bmi: float) -> str:
    # Source: classification_cutoffs.BMI1 —
    # "<18 underweight / 18-22.9 normal / 23-24.9 over weight / >25 obese"
    if bmi < 18:
        return "Underweight"
    if bmi <= 22.9:
        return "Normal"
    if bmi <= 24.9:
        return "Overweight"
    return "Obese"


def classify_waist(sex: str, waist_cm: float | None) -> str | None:
    # Source: classification_cutoffs.Waist2 — "<90cm male / <80cm female normal"
    if waist_cm is None:
        return None
    threshold = 90.0 if sex == "Male" else 80.0
    return "Normal" if waist_cm < threshold else "Abdominal obesity"


def classify_waist_hip_ratio(sex: str, waist_cm: float | None, hip_cm: float | None) -> str | None:
    # Source: classification_cutoffs.'Waist:hip ratio3' — "<0.95 male / <0.80 female normal"
    if waist_cm is None or hip_cm is None or hip_cm == 0:
        return None
    ratio = waist_cm / hip_cm
    threshold = 0.95 if sex == "Male" else 0.80
    return "Normal" if ratio < threshold else "Central obesity"


def calc_bmr(sex: str, weight_kg: float, height_cm: float, age_years: float) -> float:
    # Harris-Benedict, as specified in Nutrition_goals.docx
    if sex == "Male":
        bmr = 66.473 + 13.752 * weight_kg + 5.003 * height_cm - 6.755 * age_years
    else:
        bmr = 655.096 + 9.563 * weight_kg + 1.85 * height_cm - 4.676 * age_years
    return round(bmr, 1)


def parse_factor_range(factor_range: str) -> tuple[float, float, float]:
    """'1.4–1.6' -> (1.4, 1.6, 1.5). Handles both '-' and '–' separators."""
    nums = re.findall(r"[\d.]+", factor_range)
    lo, hi = float(nums[0]), float(nums[1])
    return lo, hi, round((lo + hi) / 2, 3)


def calc_tee(bmr: float, activity_factor: float) -> float:
    return round(bmr * activity_factor, 1)


def calc_ibw(height_cm: float) -> float:
    # IBW = 22 x Height^2 (m^2) — target BMI of 22 kg/m^2, per Nutrition_goals.docx
    height_m = height_cm / 100.0
    return round(22.0 * (height_m ** 2), 1)


def weight_change_needed(weight_kg: float, ibw_kg: float) -> dict:
    diff = round(weight_kg - ibw_kg, 1)
    if abs(diff) < 0.5:
        direction = "at ideal body weight"
    elif diff > 0:
        direction = "weight loss recommended"
    else:
        direction = "weight gain recommended"
    return {"ibw_kg": ibw_kg, "current_minus_ibw_kg": diff, "direction": direction}


def full_anthropometrics(profile: UserProfile) -> dict:
    bmi = calc_bmi(profile.weight_kg, profile.height_cm)
    bmr = calc_bmr(profile.sex, profile.weight_kg, profile.height_cm, profile.age_years)
    is_pediatric = profile.age_years < 18

    if is_pediatric:
        # BMI cutoffs (18/22.9/24.9), Harris-Benedict, and IBW=22*height^2 are all
        # adult-derived standards. None are valid for a growing child — pediatric
        # assessment needs age/sex-specific BMI-for-age growth references (e.g. WHO
        # child growth standards), which aren't in any of the three source files.
        # Surfacing the raw numbers would look authoritative while being potentially
        # wrong, so classification/IBW are explicitly withheld rather than guessed.
        bmi_classification = "Not applicable — requires pediatric BMI-for-age growth reference (not available in current data)"
        ibw = None
        weight_vs_ibw = None
        bmr_note = "Harris-Benedict is an adult-derived formula; not validated for pediatric patients"
    else:
        bmi_classification = classify_bmi(bmi)
        ibw = calc_ibw(profile.height_cm)
        weight_vs_ibw = weight_change_needed(profile.weight_kg, ibw)
        bmr_note = None

    return {
        "bmi": bmi,
        "bmi_classification": bmi_classification,
        "bmr_kcal_day": bmr,
        "bmr_note": bmr_note,
        "ibw_kg": ibw,
        "weight_vs_ibw": weight_vs_ibw,
        "waist_classification": classify_waist(profile.sex, profile.waist_cm),
        "waist_hip_ratio_classification": classify_waist_hip_ratio(
            profile.sex, profile.waist_cm, profile.hip_cm
        ),
        "is_pediatric": is_pediatric,
    }
