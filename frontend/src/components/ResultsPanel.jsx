import { buildEvaluationRows, downloadCsv } from "../exportCsv";

const STATUS_CLASS = {
  Low: "status-deficient",
  High: "status-excess",
  Deficient: "status-deficient",
  Adequate: "status-adequate",
  Excess: "status-excess",
  "No reference available": "status-unknown",
};

function StatusBadge({ status }) {
  return <span className={`badge ${STATUS_CLASS[status] || "status-unknown"}`}>{status}</span>;
}

export default function ResultsPanel({ report }) {
  if (!report) return null;
  const { age_category, macronutrients = [], nutrient_balance, entry_breakdown = [], anthropometrics: a, energy_requirement, protein_requirement, nutrient_status, disease_nutrition_goals, data_gaps } = report;

  return (
    <section className="card results">
      <h2>Analysis results</h2>
      {age_category && <p className="stat-sub">Age category: {age_category}</p>}

      <div className="stat-grid">
        <div className="stat">
          <span className="stat-label">BMI</span>
          <span className="stat-value">{a.bmi}</span>
          <span className="stat-sub">{a.bmi_classification}</span>
        </div>
        <div className="stat">
          <span className="stat-label">BMR</span>
          <span className="stat-value">{a.bmr_kcal_day}</span>
          <span className="stat-sub">kcal/day</span>
        </div>
        <div className="stat">
          <span className="stat-label">Ideal body weight</span>
          <span className="stat-value">{a.ibw_kg != null ? `${a.ibw_kg} kg` : "N/A"}</span>
          <span className="stat-sub">{a.weight_vs_ibw?.direction ?? (a.ibw_kg == null ? "see note below" : "")}</span>
        </div>
        {a.waist_classification && (
          <div className="stat">
            <span className="stat-label">Waist</span>
            <span className="stat-value">{a.waist_classification}</span>
          </div>
        )}
        {a.waist_hip_ratio_classification && (
          <div className="stat">
            <span className="stat-label">Waist:Hip</span>
            <span className="stat-value">{a.waist_hip_ratio_classification}</span>
          </div>
        )}
      </div>

      {energy_requirement && (
        <div className="req-row">
          <strong>Energy:</strong> {energy_requirement.intake_kcal} kcal consumed vs{" "}
          {energy_requirement.dri_ar_kcal_day ?? "?"} kcal DRI requirement{" "}
          (Harris-Benedict TEE: {energy_requirement.harris_benedict_tee_kcal_day ?? "n/a"} kcal){" "}
          <StatusBadge status={energy_requirement.status} />
        </div>
      )}
      {protein_requirement && (
        <div className="req-row">
          <strong>Protein:</strong> {protein_requirement.intake_g} g consumed vs{" "}
          {protein_requirement.rda_total_g_day ?? "?"} g RDA{" "}
          <StatusBadge status={protein_requirement.status} />
        </div>
      )}

      {macronutrients.length > 0 && (
        <>
          <h3>Energy &amp; macronutrients</h3>
          <table className="nutrient-table">
            <thead>
              <tr><th>Nutrient</th><th>Intake</th><th>% energy</th><th>Reference</th><th>Status</th></tr>
            </thead>
            <tbody>
              {macronutrients.map((m) => (
                <tr key={m.nutrient} title={m.note ?? ""}>
                  <td>{m.nutrient}</td>
                  <td>{m.intake} {m.unit}</td>
                  <td>{m.energy_pct != null ? `${m.energy_pct}%` : "—"}</td>
                  <td>{m.reference ?? "—"}</td>
                  <td><StatusBadge status={m.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {nutrient_balance && (
            <div className="req-row">
              <strong>Nutrient balance:</strong>{" "}
              <span className={`badge ${nutrient_balance.verdict === "Satisfactory" ? "status-adequate" : "status-deficient"}`}>
                {nutrient_balance.verdict}
              </span>
              {nutrient_balance.issues.length > 0 && <ul>{nutrient_balance.issues.map((i, k) => <li key={k}>{i}</li>)}</ul>}
              <p className="stat-sub">{nutrient_balance.note}</p>
            </div>
          )}
        </>
      )}

      <h3>Vitamins &amp; minerals</h3>
      <table className="nutrient-table">
        <thead>
          <tr><th>Nutrient</th><th>Intake</th><th>AR</th><th>RDA/AI</th><th>UL</th><th>Status</th></tr>
        </thead>
        <tbody>
          {nutrient_status.map((n) => (
            <tr key={n.nutrient}>
              <td>{n.nutrient}</td>
              <td>{n.intake} {n.unit}</td>
              <td>{n.ar ?? "—"}</td>
              <td>{n.rda ?? n.ai ?? "—"}</td>
              <td>{n.ul ?? "—"}</td>
              <td><StatusBadge status={n.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>

      {entry_breakdown.length > 0 && (
        <details className="goal-block">
          <summary><strong>Per-food calculation (for manual verification)</strong></summary>
          <table className="nutrient-table">
            <thead>
              <tr><th>Food</th><th>g</th><th>Energy</th><th>Protein</th><th>Carb</th><th>Fat</th><th>Fibre</th><th>Na</th><th>K</th><th>Ca</th><th>Fe</th></tr>
            </thead>
            <tbody>
              {entry_breakdown.map((r, i) => (
                <tr key={i}>
                  <td>{r.food_name}</td><td>{r.grams}</td>
                  {["Energy", "Protein", "Carbohydrate", "Total Fat", "Total Dietary Fibre", "Sodium", "Potassium", "Calcium", "Iron"].map((k) => (
                    <td key={k}>{r.values[k]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      <button className="analyze-btn secondary-btn" onClick={() => downloadCsv("nutrisl-intake-evaluation.csv", buildEvaluationRows(report, "Diet diary"))}>
        Download evaluation sheet (CSV)
      </button>

      {disease_nutrition_goals.length > 0 && (
        <>
          <h3>Disease-specific nutrition goals</h3>
          {disease_nutrition_goals.map((g) => (
            <div className="goal-block" key={g.disease_condition}>
              <strong>{g.disease_condition}</strong>
              <p className="goal-text">{g.nutrition_goal_text}</p>
            </div>
          ))}
        </>
      )}

      {data_gaps.length > 0 && (
        <div className="data-gaps">
          <h3>Data gaps in this report</h3>
          <ul>{data_gaps.map((g, i) => <li key={i}>{g}</li>)}</ul>
        </div>
      )}
    </section>
  );
}
