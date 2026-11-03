"""Demo mode: SYNTHETIC calibration cities, so the cascade has something to compare.

These cities are made up. Their fleets follow a power curve (k = 3) with +/-5% noise.
They are never written to the real database.
"""

import numpy as np

from imc.correction import FORMS


def synthetic_cities(true_form="power", params=(3,), rho=0.7, seed=1):
    rng = np.random.default_rng(seed)
    cities = []
    for i, R in enumerate([0.10, 0.20, 0.30, 0.40, 0.50, 0.60]):
        c = {"name": f"Synthetic {i + 1}", "country": "XX", "P": int(rng.integers(30_000, 90_000)),
             "r_dmr": 0.60, "a0": 0.22, "w_cs": 0.3947, "u": 10, "R": R,
             "synthetic": True}   # defined directly by R: no indicators to re-score
        T = c["P"] * c["r_dmr"] * c["a0"] * c["w_cs"]
        c["N_obs"] = float(rho * T * FORMS[true_form]["f"](R, list(params)) / c["u"]
                           * np.exp(rng.normal(0, 0.05)))
        cities.append(c)
    return cities
