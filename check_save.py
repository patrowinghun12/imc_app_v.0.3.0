"""Check subtask 9c: save a city from the app, then see the model learn from it.

Uses a separate check database (set through environment variables), never data/cities.json.
The second calibration city's fleet below is MADE-UP, only to show the mechanics.

Run with:  python check_save.py
"""

import os
from pathlib import Path

os.environ["IMC_CITIES_DB"] = "data/cities_save_check.json"
os.environ["IMC_SURVEYS_DB"] = "data/surveys_save_check.json"
for p in os.environ["IMC_CITIES_DB"], os.environ["IMC_SURVEYS_DB"]:
    if Path(p).exists():
        Path(p).unlink()

from streamlit.testing.v1 import AppTest
from imc.database import load_cities


def calculate(app):
    next(b for b in app.button if b.label == "Calculate").click().run()


app = AppTest.from_file("app.py", default_timeout=120).run()

# 1) Mosonmagyarovar with Konstanz only -> 18
calculate(app)
print("Before saving:", [m.value for m in app.metric][:1], "| calibration cities:",
      [c["name"] for c in load_cities(os.environ["IMC_CITIES_DB"]) if c.get("N_obs")])

# 2) Change an input -> the 'inputs changed' notice must appear
app.number_input(key="val_a0").set_value(0.25).run()
print("Notice after change:", any("inputs have changed" in w.value for w in app.warning))
app.number_input(key="val_a0").set_value(0.20).run()
calculate(app)

# 3) Pretend Mosonmagyarovar now has car sharing with 22 cars (MADE-UP) and save it
app.checkbox(key="known").check().run()                       # "real fleet is known"
app.number_input(key="N_obs").set_value(22).run()             # observed fleet
app.text_input(key="source").set_value("MADE-UP test value").run()
next(b for b in app.button if b.label == "Save as calibration city").click().run()
print("Flash message:", [s.value for s in app.success])

db = load_cities(os.environ["IMC_CITIES_DB"])
saved = next(c for c in db if c["name"] == "Mosonmagyarovar")
print("Stored test:", saved["test_before_learning"])

# 4) A new town: now 2 calibration cities -> the prediction uses both
app.text_input[0].set_value("Example town (MADE-UP)").run()
calculate(app)
print("Example town:", [m.value for m in app.metric][:1], "| caption:", app.caption[0].value)
print("App errors:", list(app.exception) or "none")