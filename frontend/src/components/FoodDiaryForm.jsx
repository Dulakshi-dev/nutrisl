import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const UNITS = ["g", "kg", "cup", "tbsp", "tsp", "ml", "l"];
const MEALS = ["breakfast", "lunch", "dinner", "snack"];

export default function FoodDiaryForm({ entries, setEntries }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    debounceRef.current = setTimeout(() => {
      api.searchFoods(query).then(setResults).catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const addEntry = (food) => {
    setEntries([
      ...entries,
      { food_code: food.food_code, food_name: food.food_name, quantity: 100, unit: "g", meal: "breakfast" },
    ]);
    setQuery("");
    setResults([]);
  };

  const updateEntry = (idx, field, value) => {
    const next = [...entries];
    next[idx] = { ...next[idx], [field]: value };
    setEntries(next);
  };

  const removeEntry = (idx) => setEntries(entries.filter((_, i) => i !== idx));

  return (
    <section className="card">
      <h2>Food diary (24-hour recall)</h2>

      <div className="food-search">
        <input
          type="text"
          placeholder="Search for a food, e.g. 'Rice' or 'Banana'..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {results.length > 0 && (
          <ul className="search-results">
            {results.map((f) => (
              <li key={f.food_code} onClick={() => addEntry(f)}>
                <span>{f.food_name}</span>
                <span className="food-group-tag">{f.food_group}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {entries.length === 0 ? (
        <p className="empty-state">No foods added yet — search above to add entries.</p>
      ) : (
        <table className="entries-table">
          <thead>
            <tr>
              <th>Food</th><th>Quantity</th><th>Unit</th><th>Meal</th><th></th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, idx) => (
              <tr key={idx}>
                <td>{entry.food_name}</td>
                <td>
                  <input
                    type="number" min="0" step="1" value={entry.quantity}
                    onChange={(e) => updateEntry(idx, "quantity", Number(e.target.value))}
                  />
                </td>
                <td>
                  <select value={entry.unit} onChange={(e) => updateEntry(idx, "unit", e.target.value)}>
                    {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
                  </select>
                </td>
                <td>
                  <select value={entry.meal} onChange={(e) => updateEntry(idx, "meal", e.target.value)}>
                    {MEALS.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </td>
                <td>
                  <button className="remove-btn" onClick={() => removeEntry(idx)}>✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
