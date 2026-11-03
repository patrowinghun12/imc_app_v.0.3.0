"""Check subtask 6: the four correction forms and fitting them to calibration cities.

Part 1 uses the real data (Konstanz only).
Part 2 uses SYNTHETIC cities generated from a known curve, to test that the fitting
finds that curve again. They are made up and never stored in the real database.

Run with:  python check_fitting.py
"""

import numpy as np

from imc.correction import FORMS, CASCADE_ORDER
from imc.fitting import fit_form, predict_with_fit

# --- Part 1: real data. One calibration city -> only the quadratic can be fitted ---
konstanz = {"name": "Konstanz", "P": 86323, "r_dmr": 0.60, "a0": 0.24, "w_cs": 0.3947,
            "u": 8.4, "R": 0.3475, "N_obs": 74}
moson = {"name": "Mosonmagyarovar", "P": 33743, "r_dmr": 0.60, "a0": 0.20, "w_cs": 0.3947,
         "u": 8.4, "R": 0.253}

print("PART 1: real data, 1 calibration city (Konstanz)")
for name in CASCADE_ORDER:
    fit = fit_form(name, [konstanz])
    if fit["ok"]:
        print(f"  {name:<11} rho = {fit['rho']:.4f}  ->  Mosonmagyarovar N = "
              f"{predict_with_fit(moson, fit):.1f}  (thesis 18.2)")
    else:
        print(f"  {name:<11} not fitted: {fit['reason']}")

# --- Part 2: synthetic cities from a KNOWN curve: power with k = 3, rho = 0.7 with u = 10 ---
rng = np.random.default_rng(seed=1)          # fixed seed -> same "random" numbers every run
true_k, true_eta = 3.0, 0.07
synthetic = []
for i, R in enumerate([0.10, 0.20, 0.30, 0.40, 0.50, 0.60]):
    city = {"name": f"Synthetic {i + 1}", "P": int(rng.integers(30_000, 90_000)),
            "r_dmr": 0.60, "a0": 0.22, "w_cs": 0.3947, "u": 10, "R": R}
    T = city["P"] * city["r_dmr"] * city["a0"] * city["w_cs"]
    noise = np.exp(rng.normal(0, 0.05))       # about +/-5% random noise, like real data
    city["N_obs"] = true_eta * T * FORMS["power"]["f"](R, [true_k]) * noise
    synthetic.append(city)

print(f"\nPART 2: 6 synthetic cities made from a power curve with k = {true_k}")
for name in CASCADE_ORDER:
    fit = fit_form(name, synthetic)
    params = ", ".join(f"{k} = {v:.2f}" for k, v in fit["params"].items()) or "none"
    flag = f"  <- at limit: {fit['at_limit']}" if fit["at_limit"] else ""
    print(f"  {name:<11} params: {params:<22} typical error = {fit['rmse_log']:.1%}{flag}")

power_fit = fit_form("power", synthetic)
ok = abs(power_fit["params"]["k"] - true_k) < 0.3
print(f"\nPower fit found k = {power_fit['params']['k']:.2f} (true {true_k})  {'OK' if ok else 'WRONG'}")