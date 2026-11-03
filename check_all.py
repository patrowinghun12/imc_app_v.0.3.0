"""Run every check of the project in one go.

Each line compares the program with a known answer (mostly your thesis numbers).
All test data go to separate *_check.json files; your real data/cities.json is never touched.
Cities called "Synthetic" or marked MADE-UP are test data, not real.

Run with:  python check_all.py
"""

import os
from pathlib import Path

# The app test below must use check files, never the real database
os.environ["IMC_CITIES_DB"] = "data/cities_app_check.json"
os.environ["IMC_SURVEYS_DB"] = "data/surveys_app_check.json"
os.environ["IMC_RUNS_DB"] = "data/runs_app_check.json"
for p in Path("data").glob("*_check.json"):
    p.unlink()

from imc.ahp import ahp
from imc.topsis import indicator_weights, topsis
from imc.correction import quadratic
from imc.demand import interested_people, fleet_size
from imc.database import add_city, load_cities, calibration_cities
from imc.calibration import rho_for_city, pooled_rho, predict_fleet
from imc.surveys import add_survey, load_surveys, suggest_surveys
from imc.fitting import fit_form
from imc.cascade import run_cascade
from imc.inputs import validate_city, fill_gaps
from imc.adjustments import final_fleet
from imc.pipeline import predict
from imc.seed import seed, MOSON_MATRIX, CRITERIA, KONSTANZ_INDICATORS
from imc.demo import synthetic_cities
from imc.visual import build_frames, draw_frame

results = []


def check(label, ok, detail=""):
    """Print one check and remember whether it passed."""
    results.append(ok)
    print(f"{'OK   ' if ok else 'WRONG'}  {label:<48} {detail}")


# ---------------------------------------------------------------- shared thesis data
gw = dict(zip(CRITERIA, (float(x) for x in ahp(MOSON_MATRIX)["weights"])))
moson_ind = [
    {"code": "C1", "group": "comfort",       "kind": "cost",    "measured": 1.73,  "worst": 5,   "ideal": 1},
    {"code": "C2", "group": "cost",          "kind": "cost",    "measured": 26.39, "worst": 40,  "ideal": 20},
    {"code": "C3", "group": "cost",          "kind": "cost",    "measured": 71.59, "worst": 120, "ideal": 40},
    {"code": "C4", "group": "accessibility", "kind": "benefit", "measured": 1.9,   "worst": 0.8, "ideal": 2.4},
    {"code": "C5", "group": "accessibility", "kind": "cost",    "measured": 35,    "worst": 60,  "ideal": 20},
]


def R_of(indicators):
    w = indicator_weights(gw, [i["group"] for i in indicators])
    return topsis([i["measured"] for i in indicators], [i["worst"] for i in indicators],
                  [i["ideal"] for i in indicators], w)


konstanz = {"name": "Konstanz", "country": "DE", "P": 86323, "r_dmr": 0.60, "a0": 0.24, "w_cs": 0.3947,
            "u": 8.4, "R": R_of(KONSTANZ_INDICATORS)["R"], "N_obs": 74, "s": 0.34}
moson = {"name": "Mosonmagyarovar", "country": "HU", "P": 33743, "r_dmr": 0.60, "a0": 0.20,
         "w_cs": 0.3947, "u": 8.4, "R": R_of(moson_ind)["R"]}       # u = Konstanz's (thesis assumption)

print("\n--- 2 AHP ---")
a = ahp(MOSON_MATRIX)
check("weights 0.448 / 0.303 / 0.152 / 0.097",
      all(abs(x - e) <= 0.001 for x, e in zip(a["weights"], [0.448, 0.303, 0.152, 0.097])),
      f"{[round(float(x), 3) for x in a['weights']]}")
check("CR below 10%", a["CR"] < 0.10, f"CR = {a['CR']:.1%} (thesis 9.7%, printed matrix gives 9.8%)")

print("\n--- 3 TOPSIS ---")
w5 = indicator_weights(gw, [i["group"] for i in moson_ind])
check("indicator weights 0.357/0.264/0.264/0.057/0.057",
      [round(float(x), 3) for x in w5] == [0.357, 0.264, 0.264, 0.057, 0.057])
check("Ci Mosonmagyarovar 0.747", abs(R_of(moson_ind)["Ci"] - 0.747) < 0.001, f"{R_of(moson_ind)['Ci']:.3f}")
check("Ci Konstanz 0.653", abs(R_of(KONSTANZ_INDICATORS)["Ci"] - 0.653) < 0.001,
      f"{R_of(KONSTANZ_INDICATORS)['Ci']:.3f}")

print("\n--- 4 Forward run ---")
f_k = quadratic(konstanz["R"])
n1 = fleet_size(interested_people(86323, 0.60, 0.20, 0.3947), f_k, 10)
n2 = fleet_size(interested_people(86323, 0.60, 0.24, 0.3947), f_k, 8.4)
n3 = fleet_size(interested_people(33743, 0.60, 0.20, 0.3947), quadratic(1 - 0.706), 10)
check("Konstanz, baseline parameters: 85", round(n1) == 85, f"{n1:.1f}")
check("Konstanz, measured parameters: 122", round(n2) == 122, f"{n2:.1f}")
check("Mosonmagyarovar TDK1 (Ci 0.706): 28", round(n3) == 28, f"{n3:.1f}")

print("\n--- 5 Database + calibration ---")
add_city(konstanz, "data/cities_check.json")
add_city(moson, "data/cities_check.json")
cal = calibration_cities(load_cities("data/cities_check.json"))
rho = pooled_rho(cal)
check("database stores 2 cities, 1 calibration city", len(cal) == 1)
check("rho Konstanz 0.607 (thesis 0.6074)", abs(rho_for_city(konstanz) - 0.6074) < 0.0005,
      f"{rho_for_city(konstanz):.4f}")
check("Mosonmagyarovar 18.2 (u = 8.4)", round(predict_fleet(moson, rho), 1) == 18.2,
      f"{predict_fleet(moson, rho):.1f}")
check("u changes the fleet: u = 10 -> 15.3", round(predict_fleet(dict(moson, u=10), rho), 1) == 15.3,
      f"{predict_fleet(dict(moson, u=10), rho):.1f}")

print("\n--- 5b Survey suggestions (any number of criteria) ---")
add_survey({"city": "Mosonmagyarovar", "country": "HU", "population": 33743, "criteria": CRITERIA,
            "matrix": MOSON_MATRIX}, "data/surveys_check.json")
add_survey({"city": "Demo town (MADE-UP)", "country": "HU", "population": 38000,
            "criteria": ["cost", "accessibility"], "matrix": [[1, 3], [1 / 3, 1]]}, "data/surveys_check.json")
sug = suggest_surveys("HU", 45000, load_surveys("data/surveys_check.json"), ["cost", "comfort", "accessibility"])
check("Mosonmagyarovar recommended, reliability dropped", sug[0]["tier"] == 1 and "reliability" in sug[0]["label"])
check("weights after dropping 0.528 / 0.357 / 0.115",
      [round(sug[0]["weights"][g], 3) for g in ["cost", "comfort", "accessibility"]] == [0.528, 0.357, 0.115])
check("survey without 'comfort' marked unusable", sug[-1]["tier"] is None)
check("AHP with 7 criteria works", abs(sum(ahp([[(j + 1) / (i + 1) for j in range(7)] for i in range(7)])["weights"]) - 1) < 1e-9)

print("\n--- 6 Fitting (synthetic cities from a power curve, k = 3) ---")
syn = synthetic_cities()
pf = fit_form("power", syn)
check("power fit finds k = 3", abs(pf["params"]["k"] - 3) < 0.3, f"k = {pf['params']['k']:.2f}")
check("only quadratic fittable with 1 real city", not fit_form("log", [konstanz])["ok"])

print("\n--- 7 Cascade ---")
c1 = run_cascade(moson, [konstanz])
check("real data: quadratic, 18.2", c1["form"] == "quadratic" and round(c1["N"], 1) == 18.2, f"{c1['N']:.1f}")
new_town = {"name": "New town", "P": 50000, "r_dmr": 0.60, "a0": 0.22, "w_cs": 0.3947, "u": 10, "R": 0.35}
check("synthetic power data: power chosen", run_cascade(new_town, syn)["form"] == "power")
check("synthetic quadratic data: quadratic chosen",
      run_cascade(new_town, synthetic_cities(params=(2,)))["form"] == "quadratic")
check("R = 0.85 flagged as extrapolation", not run_cascade(dict(new_town, R=0.85), syn)["inside_range"])

print("\n--- 8 Input checks + adjustments ---")
check("a0 = 24 caught as a percentage", any("percentage" in p for p in validate_city(dict(moson, a0=24))[0]))
swapped = [dict(i) for i in moson_ind]
swapped[3]["worst"], swapped[3]["ideal"] = 2.4, 0.8
check("swapped stop-density benchmarks caught",
      any("swapped" in p for p in validate_city(dict(moson, indicators=swapped))[0]))
check("u = 1 gives a warning", any("unusual" in w for w in validate_city(dict(moson, u=1))[1]))
filled = fill_gaps({"name": "X", "country": "HU", "P": 41000}, [konstanz])
check("missing u -> calibration cities' u (8.4)", filled["u"] == 8.4)
check("missing cycling share is NOT filled", filled.get("s") is None)
ff = final_fleet(18.2, dict(moson, s=0.15, N_max=20), [konstanz])
check("cycling 15% -> 23.4, then cap 20", [round(n, 1) for _, n in ff["steps"]] == [18.2, 23.4, 20.0])

print("\n--- 9 Pipeline, animation and app ---")
seed("data/cities_pipe_check.json", "data/surveys_pipe_check.json")
city = {k: moson[k] for k in ["name", "country", "P", "r_dmr", "a0", "w_cs", "u"]}
r = predict(city, moson_ind, gw, load_cities("data/cities_pipe_check.json"))
check("pipeline: Ci 0.747, quadratic, 18.2",
      round(r["Ci"], 3) == 0.747 and r["cascade"]["form"] == "quadratic" and round(r["final"]["N"], 1) == 18.2)
for label, db in [("real", load_cities("data/cities_pipe_check.json")), ("demo", syn)]:
    rr = predict(city, moson_ind, gw, db)
    frames = build_frames(rr["cascade"], city["name"])
    for fr in frames:
        draw_frame(fr, rr["cascade"], rr["cal"]).to_dict()
    check(f"animation frames draw ({label})", True, f"{len(frames)} frames")

from streamlit.testing.v1 import AppTest
app = AppTest.from_file("app.py", default_timeout=120).run()
next(b for b in app.button if b.label == "Calculate").click().run()
check("app: Calculate shows 18 vehicles", app.metric[0].value == "18 vehicles", app.metric[0].value)
check("app: density metric 0.54 per 1,000", app.metric[1].value == "0.54", app.metric[1].value)
next(b for b in app.button if b.label == "Save calculation").click().run()
from imc.runs import load_runs as _load_runs
_saved_runs = _load_runs(os.environ["IMC_RUNS_DB"])
check("app: calculation saved (v0.3.0)", len(_saved_runs) == 1 and round(_saved_runs[0]["result"]["N"], 1) == 18.2,
      len(_saved_runs))
app.checkbox(key="known").check().run()
app.number_input(key="N_obs").set_value(22).run()
next(b for b in app.button if b.label == "Save as calibration city").click().run()
saved = load_cities(os.environ["IMC_CITIES_DB"])
check("app: save as calibration city (MADE-UP 22)", len(calibration_cities(saved)) == 2)
check("app: no errors", not list(app.exception))

print("\n--- 10 Density comparison (v0.2.0) ---")
from imc.compare import per_1000, density_table, summary
check("Konstanz 74 / 86,323 = 0.857 per 1,000", round(per_1000(74, 86323), 3) == 0.857)
rows = density_table("Mosonmagyaróvár", 33743, 18.2, 8.4, [{"name": "Konstanz", "P": 86323, "N_obs": 74, "u": 8.4}])
check("Mosonmagyaróvár 18.2 -> 0.539 per 1,000", round(rows[0]["per_1000"], 3) == 0.539)
check("estimate = 0.63 x Konstanz density", round(summary(rows)["ratio"], 2) == 0.63)
demo_run = predict({"name": "X", "country": "HU", "P": 33743, "r_dmr": 0.6, "a0": 0.2, "w_cs": 0.3947, "u": 10,
                    "s": None, "N_max": None},
                   [{"code": "C1", "name": "Crowding", "group": "comfort", "kind": "cost",
                     "measured": 1.73, "worst": 5.0, "ideal": 1.0}],
                   {"comfort": 1.0}, synthetic_cities())
check("demo mode: no 'R could not be recomputed' warnings",
      not any("could not be recomputed" in w for w in demo_run.get("warnings", [])))

print("\n--- 11 Saved calculations and PDF report (v0.3.0) ---")
import io
from pypdf import PdfReader
from imc.runs import make_run, to_json, from_json, compare_table, changed_inputs
from imc.report import build_pdf, serif_font
_cal_for_runs = load_cities("data/cities_pipe_check.json")
base = predict(dict(city, name="Mosonmagyaróvár", s=None, N_max=None), moson_ind, gw, _cal_for_runs, "automatic")
run_a = make_run(base, "Baseline", gw, "AHP (thesis matrix)", "automatic", False, "0.3.0")
check("run: fleet 18.2 frozen", round(run_a["result"]["N"], 1) == 18.2, run_a["result"]["N"])
check("run: JSON round trip", from_json(to_json(run_a)) == run_a)
alt_run = predict(dict(city, name="Mosonmagyaróvár", s=None, N_max=None, u=10), moson_ind, gw, _cal_for_runs, "automatic")
run_b = make_run(alt_run, "u = 10", gw, "AHP (thesis matrix)", "automatic", False, "0.3.0")
rows_cmp, differs_cmp, _ = compare_table([run_a, run_b])
changed = {r["quantity"] for r, d in zip(rows_cmp, differs_cmp) if d}
check("compare: u and fleet differ, Ci does not", {"Users per vehicle u", "Fleet size N"} <= changed
      and "Closeness Ci" not in changed, sorted(changed))
check("compare: change list names u", changed_inputs(run_a, run_b) == ["Users per vehicle u: 8.4 → 10.0"])
pdf = build_pdf(run_a)
text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
check("PDF: starts with %PDF and has pages", pdf[:4] == b"%PDF" and len(PdfReader(io.BytesIO(pdf)).pages) >= 2)
check("PDF: name, university, slogan", all(x in text for x in ["Patrik Lukács", "Széchenyi István University",
                                                                 "Calculate it."]))
check("PDF: serif typeface", serif_font() in ("Times New Roman", "Liberation Serif"), serif_font())

print(f"\n{sum(results)} of {len(results)} checks passed.")