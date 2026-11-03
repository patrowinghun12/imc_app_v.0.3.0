"""Check subtask 8: input checks, gap filling, modal split, operator cap.

Values marked MADE-UP are examples to test the logic, not data.

Run with:  python check_inputs.py
"""

from imc.inputs import validate_city, fill_gaps
from imc.adjustments import final_fleet
from imc.cascade import run_cascade

# Thesis indicators of Konstanz (EUR), with benchmarks
konstanz_indicators = [
    {"code": "C1", "group": "comfort",       "kind": "cost",    "measured": 1.90,   "worst": 5,      "ideal": 1},
    {"code": "C2", "group": "cost",          "kind": "cost",    "measured": 0.1193, "worst": 0.1616, "ideal": 0.0808},
    {"code": "C3", "group": "cost",          "kind": "cost",    "measured": 1.153,  "worst": 1.50,   "ideal": 0.50},
    {"code": "C4", "group": "accessibility", "kind": "benefit", "measured": 2.19,   "worst": 0.8,    "ideal": 2.4},
    {"code": "C5", "group": "accessibility", "kind": "cost",    "measured": 25.5,   "worst": 60,     "ideal": 20},
]
konstanz = {"name": "Konstanz", "country": "DE", "P": 86323, "r_dmr": 0.60, "a0": 0.24,
            "w_cs": 0.3947, "u": 8.4, "R": 0.3475, "N_obs": 74, "s": 0.34,
            "indicators": konstanz_indicators}


def show_check(label, city):
    problems, warnings = validate_city(city)
    print(f"\n{label}")
    print("  problems:", problems or "none")
    print("  warnings:", warnings or "none")


# --- 1) Validation ---
print("=== 1) INPUT CHECKS ===")
show_check("Konstanz as in the thesis:", konstanz)
show_check("a0 typed as 24 instead of 0.24:", dict(konstanz, a0=24))
swapped = [dict(i) for i in konstanz_indicators]
swapped[3]["worst"], swapped[3]["ideal"] = 2.4, 0.8          # stop density flipped (13 Oct case)
show_check("Stop density benchmarks swapped:", dict(konstanz, indicators=swapped))
beyond = [dict(i) for i in konstanz_indicators]
beyond[4]["measured"] = 15                                    # headway better than the 20-min ideal
show_check("Headway 15 min, better than the ideal:", dict(konstanz, indicators=beyond))

# --- 2) Gap filling: a new Hungarian town with a0, u and willingness missing ---
print("\n=== 2) GAP FILLING ===")
database = [konstanz,
            {"name": "Mosonmagyarovar", "country": "HU", "P": 33743, "r_dmr": 0.60,
             "a0": 0.20, "w_cs": 0.3947, "u": 10}]
new_town = {"name": "Example town (MADE-UP)", "country": "HU", "P": 41000, "r_dmr": 0.62}
filled = fill_gaps(new_town, database)
for key, how in filled["estimated"].items():
    print(f"  {key} = {filled[key]}  <- {how}")

# --- 3) Modal split + 4) operator cap, on the Mosonmagyarovar prediction (18.2) ---
print("\n=== 3) MODAL SPLIT and 4) OPERATOR CAP ===")
moson = {"name": "Mosonmagyarovar", "country": "HU", "P": 33743, "r_dmr": 0.60, "a0": 0.20,
         "w_cs": 0.3947, "u": 10, "R": 0.253}
N_model = run_cascade(moson, [konstanz])["N"]

for label, extra in [("no cycling share given", {}),
                     ("cycling share 34% (same as Konstanz)", {"s": 0.34}),
                     ("cycling share 15% (MADE-UP example)", {"s": 0.15}),
                     ("cycling 15% + operator cap 20 (MADE-UP)", {"s": 0.15, "N_max": 20})]:
    result = final_fleet(N_model, dict(moson, **extra), [konstanz])
    steps = "  ->  ".join(f"{n:.1f}" for _, n in result["steps"])
    print(f"\n  {label}: {steps}")
    for note in result["notes"]:
        print(f"    {note}")