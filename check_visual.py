"""Check subtask 9b: animation frames and charts, real data and demo mode.

Run with:  python check_visual.py
"""

from imc.seed import MOSON_MATRIX, CRITERIA, seed
from imc.ahp import ahp
from imc.database import load_cities
from imc.pipeline import predict
from imc.demo import synthetic_cities
from imc.visual import build_frames, draw_frame

w = ahp(MOSON_MATRIX)["weights"]
gw = dict(zip(CRITERIA, (float(x) for x in w)))
indicators = [
    {"code": "C1", "group": "comfort",       "kind": "cost",    "measured": 1.73,  "worst": 5,   "ideal": 1},
    {"code": "C2", "group": "cost",          "kind": "cost",    "measured": 26.39, "worst": 40,  "ideal": 20},
    {"code": "C3", "group": "cost",          "kind": "cost",    "measured": 71.59, "worst": 120, "ideal": 40},
    {"code": "C4", "group": "accessibility", "kind": "benefit", "measured": 1.9,   "worst": 0.8, "ideal": 2.4},
    {"code": "C5", "group": "accessibility", "kind": "cost",    "measured": 35,    "worst": 60,  "ideal": 20},
]
city = {"name": "Mosonmagyarovar", "country": "HU", "P": 33743,
        "r_dmr": 0.60, "a0": 0.20, "w_cs": 0.3947, "u": 10}

seed("data/cities_pipe_check.json", "data/surveys_pipe_check.json")
for label, db in [("REAL DATA (Konstanz)", load_cities("data/cities_pipe_check.json")),
                  ("DEMO (synthetic cities)", synthetic_cities())]:
    r = predict(city, indicators, gw, db)
    frames = build_frames(r["cascade"], city["name"])
    for fr in frames:
        draw_frame(fr, r["cascade"], r["cal"]).to_dict()    # builds the chart; fails if broken
    print(f"\n{label}: {len(frames)} frames, all drawn without errors")
    for fr in frames:
        if not fr["message"].startswith("Testing"):
            print("  " + fr["message"].replace("**", ""))

from streamlit.testing.v1 import AppTest
app = AppTest.from_file("app.py", default_timeout=120).run()
app.toggle[0].set_value(True).run()             # demo mode on
app.button[0].click().run()                     # Calculate
app.button[1].click().run()                     # Play
print("\nApp errors:", list(app.exception) or "none")
print("App shows:", [m.value for m in app.metric])