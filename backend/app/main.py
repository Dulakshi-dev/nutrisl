from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from .calculator import calculate_intake, search_foods
from .cooking_yield import adjust_value, RAW_FOOD_GROUPS_NEEDING_YIELD_ADJUSTMENT
from .db import get_conn
from .deficiency import analyze
from .meal_planning import generate_meal_plan
from .profile import UserProfile
from .schemas import DeficiencyReport, DiaryInput, IntakeResult, MealPlanResult


class AnalyzeRequest(BaseModel):
    profile: UserProfile
    diary: DiaryInput

app = FastAPI(title="NutriSL API", version="0.1.0")

# Wide open for local dev / demo; tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/foods")
def list_foods(q: str = "", group: str | None = None, limit: int = 50):
    return search_foods(query=q, food_group=group, limit=limit)


@app.get("/foods/{food_code}")
def get_food(food_code: str):
    conn = get_conn()
    food = conn.execute(
        "SELECT * FROM foods WHERE food_code = ?", (food_code,)
    ).fetchone()
    if food is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Food not found")
    nutrients = conn.execute(
        """
        SELECT nd.nutrient_code, nd.nutrient_name, nd.unit, fn.value
        FROM food_nutrients fn JOIN nutrient_dictionary nd ON fn.nutrient_code = nd.nutrient_code
        WHERE fn.food_code = ? ORDER BY nd.nutrient_name
        """,
        (food_code,),
    ).fetchall()
    conn.close()
    is_adjusted = food["food_group"] in RAW_FOOD_GROUPS_NEEDING_YIELD_ADJUSTMENT
    nutrients_out = []
    for n in nutrients:
        row = dict(n)
        row["value"] = adjust_value(row["value"], food["food_group"])
        nutrients_out.append(row)
    return {
        "food_code": food["food_code"],
        "food_name": food["food_name"],
        "food_group": food["food_group"],
        "nutrients_per_100g": nutrients_out,
        "cooking_yield_adjusted": is_adjusted,  # see cooking_yield.py — True means
        # these values were divided to approximate cooked-state density, not the
        # raw source-table figures
    }


@app.get("/food-groups")
def list_food_groups():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT food_group FROM foods ORDER BY food_group").fetchall()
    conn.close()
    return [r["food_group"] for r in rows]


@app.post("/calculate-intake", response_model=IntakeResult)
def calculate_intake_endpoint(diary: DiaryInput):
    if not diary.entries:
        raise HTTPException(status_code=400, detail="No diary entries provided")
    return calculate_intake(diary)


@app.get("/nutrients")
def list_nutrients():
    conn = get_conn()
    rows = conn.execute(
        "SELECT nutrient_code, nutrient_name, unit FROM nutrient_dictionary ORDER BY nutrient_name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/diseases")
def list_diseases():
    """Valid values for UserProfile.diseases — must match exactly for the goal lookup to work."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT disease_condition FROM disease_nutrition_goals ORDER BY disease_condition"
    ).fetchall()
    conn.close()
    return [r["disease_condition"] for r in rows]


@app.get("/activity-levels")
def list_activity_levels():
    """Valid values for UserProfile.occupation_activity_level."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM activity_factors").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/analyze", response_model=DeficiencyReport)
def analyze_endpoint(request: AnalyzeRequest):
    """Objective 3: full deficiency/sufficiency analysis for one profile + one day's diary."""
    if not request.diary.entries:
        raise HTTPException(status_code=400, detail="No diary entries provided")
    intake = calculate_intake(request.diary)
    return analyze(request.profile, intake)


@app.post("/generate-meal-plan", response_model=MealPlanResult)
def generate_meal_plan_endpoint(request: AnalyzeRequest):
    """
    Objective 4: generate a Sri Lankan daily meal plan targeting this profile's
    identified deficiencies and disease-specific nutrition goals. The 'diary' field
    is the most recently recorded day, used to identify what's currently deficient —
    the plan itself is a fresh recommended day, not an addition to the recalled one.
    """
    if not request.diary.entries:
        raise HTTPException(status_code=400, detail="No diary entries provided — needed to identify deficiencies first")
    return generate_meal_plan(request.profile, request.diary)
