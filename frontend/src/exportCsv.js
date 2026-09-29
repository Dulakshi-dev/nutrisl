// Builds a CSV the nutritionist can compare against their manual calculation
// (mirrors the questionnaire rows: energy, protein, carbohydrate, fat, fibre, Na, K, Ca, Fe).
const KEY_MINERALS = ["Sodium", "Potassium", "Calcium", "Iron"];

export function buildEvaluationRows(report, label) {
  if (!report) return [];
  const rows = report.macronutrients.map((m) => [label, m.nutrient, m.intake, m.unit, m.reference ?? "", m.status]);
  report.nutrient_status
    .filter((n) => KEY_MINERALS.includes(n.nutrient))
    .forEach((n) => rows.push([label, n.nutrient, n.intake, n.unit, n.rda ?? n.ai ?? n.ar ?? "", n.status]));
  return rows;
}

export function downloadCsv(filename, rows) {
  const header = ["Source", "Nutrient", "Value", "Unit", "Reference", "Status"];
  const esc = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const csv = [header, ...rows].map((r) => r.map(esc).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
