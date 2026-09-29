import { useEffect, useState } from "react";
import { api } from "../api";

const PHYS_STATUS_OPTIONS = [
  { value: "none", label: "None" },
  { value: "pregnant_trimester1", label: "Pregnant — 1st trimester" },
  { value: "pregnant_trimester2", label: "Pregnant — 2nd trimester" },
  { value: "pregnant_trimester3", label: "Pregnant — 3rd trimester" },
  { value: "lactating_0_6mo", label: "Lactating (0–6 months postpartum)" },
  { value: "lactating_gt6mo", label: "Lactating (>6 months postpartum)" },
];

const PAL_OPTIONS = ["Sedentary", "Active", "Very active"];

export default function ProfileForm({ profile, setProfile }) {
  const [activityLevels, setActivityLevels] = useState([]);
  const [diseases, setDiseases] = useState([]);

  useEffect(() => {
    api.activityLevels().then(setActivityLevels).catch(() => {});
    api.diseases().then(setDiseases).catch(() => {});
  }, []);

  const update = (field, value) => setProfile({ ...profile, [field]: value });

  const toggleDisease = (disease) => {
    const has = profile.diseases.includes(disease);
    update(
      "diseases",
      has ? profile.diseases.filter((d) => d !== disease) : [...profile.diseases, disease]
    );
  };

  return (
    <section className="card">
      <h2>Patient profile</h2>
      <div className="grid-2">
        <label>
          Patient code
          <input
            type="text" placeholder="e.g. P-001" value={profile.patient_code ?? ""}
            onChange={(e) => update("patient_code", e.target.value)}
          />
        </label>
        <label>
          Age (years)
          <input
            type="number" min="0" max="120" value={profile.age_years}
            onChange={(e) => update("age_years", Number(e.target.value))}
          />
        </label>
        <label>
          Sex
          <select value={profile.sex} onChange={(e) => update("sex", e.target.value)}>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
          </select>
        </label>
        <label>
          Weight (kg)
          <input
            type="number" min="0" step="0.1" value={profile.weight_kg}
            onChange={(e) => update("weight_kg", Number(e.target.value))}
          />
        </label>
        <label>
          Height (cm)
          <input
            type="number" min="0" step="0.1" value={profile.height_cm}
            onChange={(e) => update("height_cm", Number(e.target.value))}
          />
        </label>
        <label>
          Waist (cm) <span className="optional">optional</span>
          <input
            type="number" min="0" step="0.1" value={profile.waist_cm ?? ""}
            onChange={(e) => update("waist_cm", e.target.value ? Number(e.target.value) : null)}
          />
        </label>
        <label>
          Hip (cm) <span className="optional">optional</span>
          <input
            type="number" min="0" step="0.1" value={profile.hip_cm ?? ""}
            onChange={(e) => update("hip_cm", e.target.value ? Number(e.target.value) : null)}
          />
        </label>
        <label>
          Physiological status
          <select
            value={profile.physiological_status}
            onChange={(e) => update("physiological_status", e.target.value)}
          >
            {PHYS_STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
        <label>
          PAL category (for DRI energy table)
          <select value={profile.pal_category} onChange={(e) => update("pal_category", e.target.value)}>
            {PAL_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>
        <label>
          Occupation activity level (for BMR × factor)
          <select
            value={profile.occupation_activity_level ?? ""}
            onChange={(e) => update("occupation_activity_level", e.target.value || null)}
          >
            <option value="">— none —</option>
            {activityLevels.map((a) => (
              <option key={a.activity_level} value={a.activity_level}>
                {a.activity_level} ({a.occupation})
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="disease-list">
        <p className="field-label">Disease / condition and diet-related comorbidities (select any that apply)</p>
        <div className="checkbox-grid">
          {diseases.map((d) => (
            <label key={d} className="checkbox-item">
              <input
                type="checkbox"
                checked={profile.diseases.includes(d)}
                onChange={() => toggleDisease(d)}
              />
              {d}
            </label>
          ))}
        </div>
      </div>

      <div className="grid-2" style={{ marginTop: 18 }}>
        <label>
          Dietary preference (for meal planning)
          <select value={profile.dietary_preference} onChange={(e) => update("dietary_preference", e.target.value)}>
            <option value="none">None</option>
            <option value="vegetarian">Vegetarian</option>
            <option value="vegan">Vegan</option>
            <option value="pescatarian">Pescatarian</option>
          </select>
        </label>
        <label>
          Food dislikes <span className="optional">comma-separated, optional</span>
          <input
            type="text" placeholder="e.g. brinjal, bitter gourd"
            value={profile.food_dislikes.join(", ")}
            onChange={(e) => update("food_dislikes", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
          />
        </label>
        <label>
          Food allergies <span className="optional">comma-separated, optional</span>
          <input
            type="text" placeholder="e.g. peanut, shellfish"
            value={profile.food_allergies.join(", ")}
            onChange={(e) => update("food_allergies", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
          />
        </label>
      </div>
    </section>
  );
}
