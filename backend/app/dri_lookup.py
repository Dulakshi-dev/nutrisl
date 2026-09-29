"""
Matches a UserProfile to the correct row in the DRI reference tables.

The DRI sheets mix three kinds of age/life-stage text in the same column:
  - plain ranges: "1-3 years", "7-11 months", "18-40 years"
  - open-ended ranges: "≥ 18 years", ">70 years"
  - physiological-state rows: "Pregnancy (all trimesters)", "1st trimester",
    "Lactation (0-6 months PP)", ">6 months PP"

This module normalizes all three into a single matching function so the rest of
the app doesn't need to know about the text formats.
"""
import re
from .profile import UserProfile

_MONTHS_RANGE = re.compile(r"(\d+)\s*-\s*(\d+)\s*months")
_YEARS_RANGE = re.compile(r"(\d+)\s*-\s*(\d+)\s*years")
_YEARS_GTE = re.compile(r"[≥>=]{1,2}\s*(\d+)\s*years")
_YEARS_GT = re.compile(r">\s*(\d+)\s*years")


def parse_age_range_years(text: str) -> tuple[float, float] | None:
    if not text:
        return None
    m = _MONTHS_RANGE.search(text)
    if m:
        return int(m.group(1)) / 12, int(m.group(2)) / 12
    m = _YEARS_RANGE.search(text)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = _YEARS_GT.search(text)
    if m:
        return float(m.group(1)) + 0.01, 130.0
    m = _YEARS_GTE.search(text)
    if m:
        return float(m.group(1)), 130.0
    return None


_TRIMESTER_MAP = {
    "1st trimester": "pregnant_trimester1", "first trimester": "pregnant_trimester1",
    "2nd trimester": "pregnant_trimester2", "second trimester": "pregnant_trimester2",
    "3rd trimester": "pregnant_trimester3", "third trimester": "pregnant_trimester3",
}


def row_matches_profile(life_stage_text: str | None, sex: str | None, profile: UserProfile) -> bool:
    """Generic matcher usable against dri_vitamins/minerals (age_life_stage) or
    dri_protein/dri_energy (age) rows — pass whichever text column that table uses."""
    if not life_stage_text or "source" in life_stage_text.lower():
        return False

    if sex not in (None, "Both") and sex != profile.sex:
        return False

    low = life_stage_text.lower()

    is_pregnancy_row = "pregnan" in low or "trimester" in low
    is_lactation_row = "lactation" in low or " pp" in low or "postpartum" in low

    if is_pregnancy_row:
        if profile.physiological_status not in (
            "pregnant_trimester1", "pregnant_trimester2", "pregnant_trimester3"
        ):
            return False
        if "all trimester" in low:
            return True
        for key, status in _TRIMESTER_MAP.items():
            if key in low:
                return status == profile.physiological_status
        return True  # generic "Pregnancy" row with no trimester split

    if is_lactation_row:
        if profile.physiological_status not in ("lactating_0_6mo", "lactating_gt6mo"):
            return False
        if "0-6" in low or "first 6" in low:
            return profile.physiological_status == "lactating_0_6mo"
        if ">6" in low or "6 month" in low and "first" not in low:
            return profile.physiological_status == "lactating_gt6mo"
        return True  # generic lactation row with no stage split

    # Plain age-range row: only applies to non-pregnant, non-lactating profiles
    if profile.physiological_status != "none":
        return False
    age_range = parse_age_range_years(life_stage_text)
    if age_range is None:
        return False
    lo, hi = age_range
    return lo <= profile.age_years <= hi


def lookup_vitamin(conn, vitamin_name: str, profile: UserProfile):
    rows = conn.execute(
        "SELECT * FROM dri_vitamins WHERE vitamin = ?", (vitamin_name,)
    ).fetchall()
    for row in rows:
        if row_matches_profile(row["age_life_stage"], row["sex"], profile):
            return dict(row)
    return None


def lookup_mineral(conn, mineral_name: str, profile: UserProfile):
    rows = conn.execute(
        "SELECT * FROM dri_minerals WHERE mineral = ?", (mineral_name,)
    ).fetchall()
    for row in rows:
        if row_matches_profile(row["age_life_stage"], row["sex"], profile):
            return dict(row)
    return None


def lookup_protein(conn, profile: UserProfile):
    rows = conn.execute("SELECT * FROM dri_protein").fetchall()
    for row in rows:
        if row_matches_profile(row["age"], row["sex"], profile):
            return dict(row)
    return None


def lookup_energy(conn, profile: UserProfile):
    rows = conn.execute("SELECT * FROM dri_energy").fetchall()
    candidates = [r for r in rows if row_matches_profile(r["age"], r["sex"], profile)]
    if not candidates:
        return None
    # Prefer the row matching the profile's PAL category; fall back to the first match
    # (pregnancy/lactation rows in this sheet only have a single 'Sedentary' entry).
    for row in candidates:
        if row["pal_activity"] == profile.pal_category:
            return dict(row)
    return dict(candidates[0])
