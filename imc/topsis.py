"""Reference-based TOPSIS (thesis Eqs. 7-14).

The decision matrix has only three rows: worst benchmark, the city, ideal benchmark.
The ideal and worst points are the benchmark rows themselves, not the best and worst
of several cities, so a city can be scored on its own.
"""

import numpy as np


def indicator_weights(group_weights, indicator_groups):
    """Turn AHP group weights into one weight per indicator.

    group_weights:    e.g. {"cost": 0.448, "comfort": 0.303, "reliability": 0.152, "accessibility": 0.097}
    indicator_groups: the group of each indicator, e.g. ["comfort", "cost", "cost", "accessibility", "accessibility"]

    Groups with no indicator (reliability in the thesis) are dropped and the rest are
    rescaled to sum to 1. A group's weight is then shared equally among its indicators.
    """
    used = set(indicator_groups)                                   # groups that have at least one indicator
    total = sum(w for g, w in group_weights.items() if g in used)  # e.g. 1 - 0.152 = 0.848

    weights = []
    for g in indicator_groups:
        count = indicator_groups.count(g)                          # how many indicators share this group
        weights.append(group_weights[g] / total / count)
    return np.array(weights)


def topsis(measured, worst, ideal, weights):
    """Score one city between a worst and an ideal benchmark.

    measured, worst, ideal, weights: one value per indicator, all in the same order.
    Returns a dictionary with Ci (closeness, 0 = worst, 1 = ideal), R = 1 - Ci, and D+ / D-.
    """
    # Decision matrix: 3 rows x n indicators.  Row 0 = worst, row 1 = city, row 2 = ideal.
    X = np.array([worst, measured, ideal], dtype=float)
    w = np.array(weights, dtype=float)

    # Vector normalisation: divide each column by its length sqrt(sum of squares).
    # This removes the units (minutes, HUF, stops/km) so the columns can be compared.
    N = X / np.sqrt((X ** 2).sum(axis=0))

    # Weighted normalised matrix: multiply each column by its indicator weight.
    V = N * w

    worst_pt, city_pt, ideal_pt = V[0], V[1], V[2]

    # Euclidean distance of the city from the ideal (D+) and from the worst case (D-).
    d_plus = np.sqrt(((city_pt - ideal_pt) ** 2).sum())
    d_minus = np.sqrt(((city_pt - worst_pt) ** 2).sum())

    ci = d_minus / (d_plus + d_minus)   # relative closeness to the ideal

    return {"Ci": ci, "R": 1 - ci, "D_plus": d_plus, "D_minus": d_minus}