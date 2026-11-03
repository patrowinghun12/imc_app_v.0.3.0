"""Check subtask 7: the selection cascade.

Scenario A uses the real data. B-E use SYNTHETIC cities (made up, never stored).

Run with:  python check_cascade.py
"""

import numpy as np

from imc.correction import FORMS
from imc.cascade import run_cascade


def make_synthetic(true_form, params, eta=0.07, seed=1):
    """6 made-up calibration cities whose fleets follow a known curve (+/-5% noise)."""
    rng = np.random.default_rng(seed)
    cities = []
    for i, R in enumerate([0.10, 0.20, 0.30, 0.40, 0.50, 0.60]):
        c = {"name": f"Synthetic {i + 1}", "P": int(rng.integers(30_000, 90_000)),
             "r_dmr": 0.60, "a0": 0.22, "w_cs": 0.3947, "u": 10, "R": R}
        T = c["P"] * c["r_dmr"] * c["a0"] * c["w_cs"]
        c["N_obs"] = eta * T * FORMS[true_form]["f"](R, params) * np.exp(rng.normal(0, 0.05))
        cities.append(c)
    return cities


def show(title, result):
    """Print the step-by-step log, the warnings and the result."""
    print(f"\n=== {title} ===")
    for line in result["log"]:
        print("  " + line)
    for w in result["warnings"]:
        print("  WARNING: " + w)
    alt = ", ".join(f"{k} {v:.1f}" for k, v in result["alternatives"].items())
    print(f"  -> form: {result['form']}, N = {result['N']:.1f}   (all fittable forms: {alt})")


konstanz = {"name": "Konstanz", "P": 86323, "r_dmr": 0.60, "a0": 0.24, "w_cs": 0.3947,
            "u": 8.4, "R": 0.3475, "N_obs": 74}
moson = {"name": "Mosonmagyarovar", "P": 33743, "r_dmr": 0.60, "a0": 0.20, "w_cs": 0.3947,
         "u": 8.4, "R": 0.253}
new_town = {"name": "New town", "P": 50000, "r_dmr": 0.60, "a0": 0.22, "w_cs": 0.3947, "u": 10, "R": 0.35}

# A) Real data: 1 city -> quadratic, warning, 18.2
a = run_cascade(moson, [konstanz])
show("A  real data, Konstanz only", a)
print(f"  check: {'OK' if a['form'] == 'quadratic' and round(a['N'], 1) == 18.2 else 'WRONG'}")

# B) Truth = power k = 3 -> power should win
b = run_cascade(new_town, make_synthetic("power", [3]))
show("B  synthetic, truth = power k = 3", b)
print(f"  check: {'OK' if b['form'] == 'power' else 'WRONG'}")

# C) Truth = quadratic -> quadratic should win (power fits equally well but costs a parameter)
c = run_cascade(new_town, make_synthetic("power", [2]))
show("C  synthetic, truth = quadratic (k = 2)", c)
print(f"  check: {'OK' if c['form'] == 'quadratic' else 'WRONG'}")

# D) Same data as B, but the user forces 'log'
d = run_cascade(new_town, make_synthetic("power", [3]), forced="log")
show("D  synthetic power k = 3, user forces 'log'", d)

# E) New city far outside the data (R = 0.85, data only 0.10-0.60)
far_town = dict(new_town, name="Far town", R=0.85)
e = run_cascade(far_town, make_synthetic("power", [3]))
show("E  synthetic power k = 3, new city at R = 0.85", e)
print(f"  check: {'OK' if not e['inside_range'] else 'WRONG'}")