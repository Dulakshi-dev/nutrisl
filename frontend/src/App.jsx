import { useState } from "react";
import ProfileForm from "./components/ProfileForm";
import FoodDiaryForm from "./components/FoodDiaryForm";
import ResultsPanel from "./components/ResultsPanel";
import MealPlanPanel from "./components/MealPlanPanel";
import { api } from "./api";
import "./App.css";

const DEFAULT_PROFILE = {
  age_years: 30,
  sex: "Female",
  weight_kg: 60,
  height_cm: 160,
  waist_cm: null,
  hip_cm: null,
  physiological_status: "none",
  pal_category: "Sedentary",
  occupation_activity_level: null,
  diseases: [],
  dietary_preference: "none",
  food_dislikes: [],
  food_allergies: [],
};

export default function App() {
  const [profile, setProfile] = useState(DEFAULT_PROFILE);
  const [entries, setEntries] = useState([]);
  const [report, setReport] = useState(null);
  const [mealPlan, setMealPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [planLoading, setPlanLoading] = useState(false);
  const [error, setError] = useState(null);

  const buildDiary = () => ({
    entries: entries.map(({ food_code, quantity, unit, meal }) => ({
      food_code, quantity, unit, meal,
    })),
  });

  const runAnalysis = async () => {
    if (entries.length === 0) {
      setError("Add at least one food diary entry before analyzing.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await api.analyze(profile, buildDiary());
      setReport(result);
    } catch (e) {
      setError(e.message);
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const runMealPlan = async () => {
    if (entries.length === 0) {
      setError("Add at least one food diary entry first — the plan is built from identified deficiencies.");
      return;
    }
    setPlanLoading(true);
    setError(null);
    try {
      const result = await api.generateMealPlan(profile, buildDiary());
      setMealPlan(result);
    } catch (e) {
      setError(e.message);
      setMealPlan(null);
    } finally {
      setPlanLoading(false);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>NutriSL</h1>
        <p className="subtitle">Digital Nutritional Assessment for Sri Lanka</p>
      </header>

      <ProfileForm profile={profile} setProfile={setProfile} />
      <FoodDiaryForm entries={entries} setEntries={setEntries} />

      <div className="action-row">
        <button className="analyze-btn" onClick={runAnalysis} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze intake"}
        </button>
        <button className="analyze-btn secondary-btn" onClick={runMealPlan} disabled={planLoading}>
          {planLoading ? "Generating..." : "Generate meal plan"}
        </button>
        {error && <span className="error-text">{error}</span>}
      </div>

      <ResultsPanel report={report} />
      <MealPlanPanel plan={mealPlan} />
    </div>
  );
}
