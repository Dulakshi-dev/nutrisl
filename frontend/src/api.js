const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request to ${path} failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  searchFoods: (q, group) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (group) params.set("group", group);
    return request(`/foods?${params.toString()}`);
  },
  foodGroups: () => request("/food-groups"),
  diseases: () => request("/diseases"),
  activityLevels: () => request("/activity-levels"),
  analyze: (profile, diary) =>
    request("/analyze", { method: "POST", body: JSON.stringify({ profile, diary }) }),
  generateMealPlan: (profile, diary) =>
    request("/generate-meal-plan", { method: "POST", body: JSON.stringify({ profile, diary }) }),
};
