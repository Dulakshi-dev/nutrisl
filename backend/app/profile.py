from typing import Literal
from pydantic import BaseModel, Field

PhysiologicalStatus = Literal[
    "none", "pregnant_trimester1", "pregnant_trimester2", "pregnant_trimester3",
    "lactating_0_6mo", "lactating_gt6mo",
]

PalCategory = Literal["Sedentary", "Active", "Very active"]

DietaryPreference = Literal["none", "vegetarian", "vegan", "pescatarian"]


class UserProfile(BaseModel):
    age_years: float = Field(..., ge=0, le=120)
    sex: Literal["Male", "Female"]
    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    waist_cm: float | None = None
    hip_cm: float | None = None
    physiological_status: PhysiologicalStatus = "none"
    pal_category: PalCategory = "Sedentary"  # used for DRI energy table lookup
    occupation_activity_level: str | None = Field(
        None, description="Must match an activity_factors.activity_level value, "
                           "e.g. 'Sedentary', 'Light', 'Moderate' — used for the "
                           "Harris-Benedict BMR x factor estimate, separate from pal_category."
    )
    diseases: list[str] = Field(
        default_factory=list,
        description="Must match disease_nutrition_goals.disease_condition values exactly "
                    "(see GET /diseases for valid options).",
    )
    dietary_preference: DietaryPreference = Field(
        "none", description="vegetarian excludes fish/meat/poultry (dairy & eggs still allowed); "
                             "vegan additionally excludes dairy & eggs; pescatarian excludes "
                             "meat/poultry but keeps fish."
    )
    food_dislikes: list[str] = Field(
        default_factory=list,
        description="Food names (or substrings) to exclude from meal plan generation, "
                    "e.g. ['brinjal', 'bitter gourd']. Case-insensitive substring match.",
    )
    food_allergies: list[str] = Field(
        default_factory=list,
        description="Same matching as food_dislikes, but semantically an allergy — kept as a "
                    "separate field since a nutrition professional may want to treat these with "
                    "zero tolerance vs. dislikes being soft preferences.",
    )
