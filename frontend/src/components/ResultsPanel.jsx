const STATUS_CLASS = {
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
  const { anthropometrics: a, energy_requirement, protein_requirement, fibre_requirement, nutrient_status, disease_nutrition_goals, data_gaps } = report;

  return (
    <section className="card results">
      <h2>Analysis results</h2>

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
      {fibre_requirement && (
        <div className="req-row">
          <strong>Dietary Fibre:</strong> {fibre_requirement.intake_g} g consumed vs{" "}
          {fibre_requirement.target_g_day} g target{" "}
          <StatusBadge status={fibre_requirement.status} />
        </div>
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
