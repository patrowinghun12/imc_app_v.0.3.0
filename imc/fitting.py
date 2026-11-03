"""Fit a correction form to the calibration cities.

For a form with shape parameters p we look for the p that makes the predicted fleets
closest to the observed ones:

    error of city i = ln(N_obs_i) - ln(N_pred_i)        (log error: 0.1 = about 10% off)
    best p          = the p with the smallest sum of squared log errors

For any p, the best level rho is the geometric mean of subtask 5, so only the shape is searched.
"""

import math

import numpy as np
from scipy.optimize import minimize

from imc.correction import FORMS
from imc.calibration import pooled_rho, predict_fleet


def _curve(form, p):
    """Turn a form + parameter values into a plain function of R, as calibration.py expects."""
    return lambda R: form["f"](R, p)


def _log_errors(form, p, cal_cities):
    """Log error of every calibration city for parameters p."""
    f = _curve(form, p)
    rho = pooled_rho(cal_cities, f)
    return [math.log(c["N_obs"]) - math.log(predict_fleet(c, rho, f)) for c in cal_cities]


def fit_form(name, cal_cities):
    """Fit one form. Returns a dictionary; 'ok' is False if there aren't enough cities."""
    form = FORMS[name]
    n_shape = len(form["params"])
    n_cities = len(cal_cities)

    # The level rho always needs 1 city; every shape parameter needs 1 more.
    needed = n_shape + 1
    if n_cities < needed:
        return {"ok": False, "name": name,
                "reason": f"needs at least {needed} calibration cities, has {n_cities}"}

    def loss(p):
        """Sum of squared log errors: the number the optimiser makes as small as possible."""
        return sum(e ** 2 for e in _log_errors(form, p, cal_cities))

    if n_shape == 0:
        best = []                                    # quadratic: nothing to search
    else:
        # Try several starting points, because the optimiser can get stuck in a local dip.
        starts = [form["start"]] + [[lo + (hi - lo) * t for lo, hi in form["bounds"]]
                                    for t in (0.1, 0.5, 0.9)]
        results = [minimize(loss, x0=s, bounds=form["bounds"], method="L-BFGS-B") for s in starts]
        best = list(min(results, key=lambda r: r.fun).x)

    errors = _log_errors(form, best, cal_cities)
    f = _curve(form, best)

    # A parameter sitting on its limit means the data want a value outside the plausible range.
    at_limit = [pname for pname, v, (lo, hi) in zip(form["params"], best, form["bounds"])
                if abs(v - lo) < 0.01 * (hi - lo) or abs(v - hi) < 0.01 * (hi - lo)]

    Rs = [c["R"] for c in cal_cities]
    return {
        "ok": True,
        "name": name,
        "params": dict(zip(form["params"], (float(v) for v in best))),
        "p": best,
        "rho": pooled_rho(cal_cities, f),
        "rmse_log": math.sqrt(np.mean([e ** 2 for e in errors])),      # typical error, 0.10 ~ 10%
        "errors": {c["name"]: e for c, e in zip(cal_cities, errors)},
        "at_limit": at_limit,
        "R_range": (min(Rs), max(Rs)),               # R values the fit has actually seen
    }


def predict_with_fit(city, fit):
    """Fleet for any city with a fitted form."""
    f = _curve(FORMS[fit["name"]], fit["p"])
    return predict_fleet(city, fit["rho"], f)