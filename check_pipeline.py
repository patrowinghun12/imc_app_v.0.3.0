"""Check subtask 9a: the full pipeline gives the thesis result, and the app starts without errors.

Run with:  python check_pipeline.py
"""

from pathlib import Path

from imc.seed import seed, MOSON_MATRIX, CRITERIA
from imc.database import load_cities
from imc.ahp import ahp
from imc.pipeline import predict

# Seed a separate check database (Konstanz as the calibration city)
for p in ["data/cities_pipe_check.json", "data/surveys_pipe_check.json"]:
    if Path(p).exists():
        Path(p).unlink()
seed("data/cities_pipe_check.json", "data/surveys_pipe_check.json")
db = load_cities("data/cities_pipe_check.json")

w = ahp(MOSON_MATRIX)["weights"]
group_weights = dict(zip(CRITERIA, (float(x) for x in w)))
indicators = [
    {"code": "C1", "group": "comfort",       "kind": "cost",    "measured": 1.73,  "worst": 5,   "ideal": 1},
    {"code": "C2", "group": "cost",          "kind": "cost",    "measured": 26.39, "worst": 40,  "ideal": 20},
    {"code": "C3", "group": "cost",          "kind": "cost",    "measured": 71.59, "worst": 120, "ideal": 40},
    {"code": "C4", "group": "accessibility", "kind": "benefit", "measured": 1.9,   "worst": 0.8, "ideal": 2.4},
    {"code": "C5", "group": "accessibility", "kind": "cost",    "measured": 35,    "worst": 60,  "ideal": 20},
]
city = {"name": "Mosonmagyarovar", "country": "HU", "P": 33743,
        "r_dmr": 0.60, "a0": 0.20, "w_cs": 0.3947, "u": 10}

r = predict(city, indicators, group_weights, db)
print(f"Ci = {r['Ci']:.3f}, form = {r['cascade']['form']}, N = {r['final']['N']:.1f}  "
      f"(thesis 0.747 / 18.2)  {'OK' if round(r['final']['N'], 1) == 18.2 else 'WRONG'}")

# The app itself: start it without a browser and check nothing crashes
from streamlit.testing.v1 import AppTest
app = AppTest.from_file("app.py", default_timeout=60).run()
app.button[0].click().run()
print("App errors:", list(app.exception) or "none")
print("App shows:", [m.value for m in app.metric])