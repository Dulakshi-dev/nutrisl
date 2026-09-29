const MEAL_LABELS = {
  breakfast: "Breakfast", lunch: "Lunch", dinner: "Dinner",
  beverage: "Beverage", dessert: "Dessert / Fruit",
};

export default function MealPlanPanel({ plan }) {
  if (!plan) return null;

  if (!plan.generated) {
    return (
      <section className="card">
        <h2>Meal plan</h2>
        <div className="data-gaps">
          <h3>Plan not generated</h3>
          <p>{plan.reason}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Generated meal plan</h2>
      {Object.entries(plan.meals).map(([meal, items]) => (
        items.length > 0 && (
          <div key={meal} className="meal-block">
            <h3>{MEAL_LABELS[meal] || meal}</h3>
            <ul className="meal-items">
              {items.map((it, i) => (
                <li key={i}>
                  <span className="meal-role">{it.role}</span>
                  {it.food_name} — {it.grams}g
                  <span className="food-group-tag"> ({it.food_group})</span>
                </li>
              ))}
            </ul>
          </div>
        )
      ))}

      {plan.limitations.length > 0 && (
        <div className="data-gaps">
          <h3>Limitations of this plan</h3>
          <ul>{plan.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
        </div>
      )}
    </section>
  );
}
