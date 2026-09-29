from pydantic import BaseModel, Field


class DiaryEntry(BaseModel):
    food_code: str = Field(..., description="e.g. 'SLA001'")
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., description="g, kg, cup, tbsp, tsp, ml, l, or a food-specific unit")
    meal: str | None = Field(None, description="e.g. breakfast, lunch, dinner, snack")


class DiaryInput(BaseModel):
    entries: list[DiaryEntry]


class NutrientTotal(BaseModel):
    nutrient_code: str
    nutrient_name: str | None
    unit: str | None
    total_value: float


class EntryResolution(BaseModel):
    food_code: str
    food_name: str
    quantity: float
    unit: str
    grams: float
    meal: str | None


class IntakeResult(BaseModel):
    resolved_entries: list[EntryResolution]
    nutrient_totals: list[NutrientTotal]
    unresolved_entries: list[dict]  # {food_code, quantity, unit, error}
    entry_breakdown: list[dict] = []  # per-food key nutrients, for manual verification


class NutrientStatus(BaseModel):
    nutrient: str
    unit: str
    intake: float
    ar: float | None = None
    rda: float | None = None
    ul: float | None = None
    ai: float | None = None
    status: str  # "Deficient" | "Adequate" | "Excess" | "No reference available"
    note: str | None = None


class MacroStatus(BaseModel):
    nutrient: str
    unit: str
    intake: float
    energy_pct: float | None = None
    reference: str | None = None
    status: str
    note: str | None = None


class DeficiencyReport(BaseModel):
    age_category: str = ""
    macronutrients: list[MacroStatus] = []
    nutrient_balance: dict | None = None  # {verdict, issues}
    entry_breakdown: list[dict] = []
    anthropometrics: dict
    energy_requirement: dict | None
    protein_requirement: dict | None
    nutrient_status: list[NutrientStatus]
    disease_nutrition_goals: list[dict]  # [{disease_condition, nutrition_goal_text}]
    data_gaps: list[str]  # things the report could NOT evaluate and why


class MealPlanItem(BaseModel):
    meal: str  # breakfast/lunch/dinner/snack
    role: str  # starch/protein/vegetable/fruit_or_nut
    food_code: str
    food_name: str
    food_group: str
    grams: float


class MealPlanResult(BaseModel):
    generated: bool
    reason: str | None  # populated when generated=False (e.g. PKU, infant-only conditions)
    meals: dict[str, list[MealPlanItem]]
    items: list[MealPlanItem]
    validation: DeficiencyReport | None  # the generated plan run back through calculate_intake+analyze
    target_energy_kcal: float | None = None
    portion_scale_factor: float | None = None
    limitations: list[str]  # goal-text items this engine could not enforce, GI-match coverage, etc.
