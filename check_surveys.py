"""Check subtask 5b: AHP survey library and suggestions.

Only Mosonmagyarovar is a real survey. "Demo town A/B/C" are MADE-UP test entries,
there only to show how the ranking works. They are stored in a check file, not the real library.

Run with:  python check_surveys.py
"""

from pathlib import Path

from imc.surveys import add_survey, load_surveys, suggest_surveys, manual_weights, size_class

CRITERIA = ["cost", "comfort", "reliability", "accessibility"]

db = Path("data/surveys_check.json")
if db.exists():
    db.unlink()

# --- Real survey: Mosonmagyarovar (thesis Table 3.1, 71 respondents) ---
add_survey({"city": "Mosonmagyarovar", "country": "HU", "population": 33743,
            "criteria": CRITERIA, "respondents": 71, "year": 2025,
            "matrix": [[1,     2.507, 3.169, 2.914],
                       [0.399, 1,     3.400, 3.414],
                       [0.316, 0.294, 1,     2.563],
                       [0.343, 0.293, 0.390, 1]]}, db)

# --- MADE-UP demo surveys (equal-ish judgements, just to test the ranking) ---
demo = [[1, 2, 2, 2], [0.5, 1, 2, 2], [0.5, 0.5, 1, 2], [0.5, 0.5, 0.5, 1]]
add_survey({"city": "Demo town A", "country": "HU", "population": 60000,
            "criteria": CRITERIA, "matrix": demo}, db)
add_survey({"city": "Demo city B", "country": "DE", "population": 250000,
            "criteria": CRITERIA, "matrix": demo}, db)
add_survey({"city": "Demo town C", "country": "AT", "population": 40000,
            "criteria": ["cost", "comfort", "accessibility"],          # only 3 criteria
            "matrix": [[1, 2, 2], [0.5, 1, 2], [0.5, 0.5, 1]]}, db)

surveys = load_surveys(db)
print(f"Surveys stored: {[s['city'] for s in surveys]}\n")


def show(label, country, population):
    """Print the ranked suggestions for one new city."""
    print(f"New city: {label} ({country}, {population:,}, {size_class(population)})")
    # The city has indicators for 3 criteria (no reliability indicator, as in the thesis)
    for s in suggest_surveys(country, population, surveys, ["cost", "comfort", "accessibility"]):
        w = ", ".join(f"{k} {v:.3f}" for k, v in s["weights"].items())
        print(f"  [{s['label']}] {s['survey']['city']}: {s['reason']}")
        print(f"      weights: {w}")
    print()


show("Hungarian town", "HU", 45000)   # expect: Mosonmagyarovar first, Demo town A second
show("Konstanz", "DE", 86323)         # expect: no tier 1; Mosonmagyarovar 'possible'

# --- Manual input: any positive numbers, rescaled to sum to 1 ---
print("Manual input {cost 5, comfort 3, reliability 1, accessibility 1} ->")
print("  ", {k: round(v, 2) for k, v in manual_weights(
    {"cost": 5, "comfort": 3, "reliability": 1, "accessibility": 1}).items()})