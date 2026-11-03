"""Correction functions f(R): how much of the interested demand becomes real use.

R = 1 - Ci is the public-transport deficiency (0 = ideal PT, 1 = worst PT).
Worse PT -> larger R -> larger f(R) -> more car-sharing demand.

All four forms share the same two anchor points, so they only differ in SHAPE:
    f(0) = m   (floor: some use even with ideal PT)
    f(1) = 1   (worst PT: everyone interested uses it)
The overall LEVEL is set by eta in the calibration, not here.

Cascade order (subtask 7): quadratic -> log -> power -> saturation.
"""

import math

M_FLOOR = 0.10   # the thesis floor m


def quadratic(R, m=M_FLOOR, k=2):
    """Thesis baseline: f = m + (1 - m) * R^2.  No free parameter: the curve is fixed."""
    return m + (1 - m) * R ** k


def logarithmic(R, c, m=M_FLOOR):
    """f = m + (1 - m) * ln(1 + c*R) / ln(1 + c)

    Rises FAST at small R and flattens later (the opposite of the quadratic).
    c = curvature: small c -> almost a straight line, large c -> rises very early.
    """
    return m + (1 - m) * math.log(1 + c * R) / math.log(1 + c)


def power(R, k, m=M_FLOOR):
    """f = m + (1 - m) * R^k  -- the quadratic, but with the exponent k fitted from data.

    k = 2 is the thesis quadratic. k > 2: demand stays low until PT is quite bad.
    k < 2: demand rises earlier. (This is the k of thesis Eq. 14.)
    """
    return m + (1 - m) * R ** k


def saturation(R, R0, s, m=M_FLOOR):
    """S-curve: low, then rises around R0, then flattens into a plateau.

    R0 = where the rise happens (the midpoint)
    s  = how sharp the rise is (small s -> a steep step, large s -> a gentle slope)
    The logistic curve is rescaled so that f(0) = m and f(1) = 1 like the other forms.
    """
    def logistic(x):
        return 1 / (1 + math.exp(-(x - R0) / s))

    share = (logistic(R) - logistic(0)) / (logistic(1) - logistic(0))   # 0 at R=0, 1 at R=1
    return m + (1 - m) * share


# Everything the fitting and the cascade need to know about each form, in one place.
#   params : names of the parameters that are fitted from data
#   bounds : plausible range of each parameter (the plausibility check of subtask 7)
#   start  : first guess for the fitting
#   f      : f(R, p) where p is the list of parameter values
FORMS = {
    "quadratic": {
        "params": [], "bounds": [], "start": [],
        "f": lambda R, p: quadratic(R),
        "about": "thesis baseline, fixed shape",
    },
    "log": {
        "params": ["c"], "bounds": [(0.1, 100)], "start": [5],
        "f": lambda R, p: logarithmic(R, p[0]),
        "about": "rises early, flattens later",
    },
    "power": {
        "params": ["k"], "bounds": [(0.5, 6)], "start": [2],
        "f": lambda R, p: power(R, p[0]),
        "about": "quadratic with a fitted exponent",
    },
    "saturation": {
        "params": ["R0", "s"], "bounds": [(0.05, 0.95), (0.02, 0.5)], "start": [0.4, 0.1],
        "f": lambda R, p: saturation(R, p[0], p[1]),
        "about": "S-curve with a plateau",
    },
}

CASCADE_ORDER = ["quadratic", "log", "power", "saturation"]