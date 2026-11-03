"""Check: the whole chain works with ANY number of criteria (n), not only 4.

Everything except the Mosonmagyarovar survey is MADE-UP test data.

Run with:  python check_n_criteria.py
"""

from pathlib import Path

from imc.ahp import ahp
from imc.topsis import indicator_weights, topsis
from imc.surveys import add_survey, load_surveys, suggest_surveys


def demo_matrix(n):
    """A made-up consistent n x n matrix: criterion i is (j+1)/(i+1) times as important as j."""
    return [[(j + 1) / (i + 1) for j in range(n)] for i in range(n)]


# --- 1) AHP alone with n = 3, 5, 7: weights always sum to 1, CR is computed ---
print("AHP with different n:")
for n in [3, 5, 7]:
    r = ahp(demo_matrix(n))
    print(f"  n = {n}: weights {[round(float(w), 3) for w in r['weights']]}, "
          f"sum = {sum(r['weights']):.3f}, CR = {r['CR']:.1%}")

# --- 2) n = 11 must be refused with a clear message, not a crash ---
try:
    ahp(demo_matrix(11))
except ValueError as error:
    print(f"  n = 11: refused -> {error}")

# --- 3) Survey suggestion with a 3-criteria city ---
db = Path("data/surveys_n_check.json")
if db.exists():
    db.unlink()
add_survey({"city": "Mosonmagyarovar", "country": "HU", "population": 33743,          # real, 4 criteria
            "criteria": ["cost", "comfort", "reliability", "accessibility"],
            "matrix": [[1, 2.507, 3.169, 2.914], [0.399, 1, 3.400, 3.414],
                       [0.316, 0.294, 1, 2.563], [0.343, 0.293, 0.390, 1]]}, db)
add_survey({"city": "Demo town C", "country": "HU", "population": 40000,              # made up, 3 criteria
            "criteria": ["cost", "comfort", "accessibility"],
            "matrix": [[1, 2, 2], [0.5, 1, 2], [0.5, 0.5, 1]]}, db)
add_survey({"city": "Demo town D", "country": "HU", "population": 38000,              # made up, lacks comfort
            "criteria": ["cost", "accessibility"],
            "matrix": [[1, 3], [1 / 3, 1]]}, db)

city_criteria = ["cost", "comfort", "accessibility"]     # this city has indicators for 3 criteria
print(f"\nCity with indicators for {city_criteria}:")
suggestions = suggest_surveys("HU", 45000, load_surveys(db), city_criteria)
for s in suggestions:
    w = ", ".join(f"{k} {v:.3f}" for k, v in s["weights"].items())
    print(f"  [{s['label']}] {s['survey']['city']}: {w}")

# --- 4) Full chain with the Mosonmagyarovar survey: 4-criteria survey, 3-criteria city ---
#        Must give the thesis Ci, because the thesis did exactly this (dropped reliability).
best = next(s for s in suggestions if s["survey"]["city"] == "Mosonmagyarovar")
weights = indicator_weights(best["weights"], ["comfort", "cost", "cost", "accessibility", "accessibility"])
ci = topsis([1.73, 26.39, 71.59, 1.9, 35], [5, 40, 120, 0.8, 60], [1, 20, 40, 2.4, 20], weights)["Ci"]
print(f"\nMosonmagyarovar scored with '{best['survey']['city']}' weights: Ci = {ci:.3f}  "
      f"(thesis 0.747 {'OK' if abs(ci - 0.747) < 0.001 else 'WRONG'})")