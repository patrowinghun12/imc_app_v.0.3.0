"""AHP survey library: stored surveys, and which one to suggest for a new city.

Each survey is stored with its criteria names, so weights are never matched
to the wrong criteria (Konstanz dropped reliability, another city might add one).

Suggestion ranking (decided 20 Oct 2026):
  1 recommended  - same country AND same size class
  2 possible     - same size class, other country (check transferability)
  3 not advised  - different size class
  A survey missing a criterion the city needs is listed but can't be used.
  Extra survey criteria without an indicator are dropped and the rest rescaled.
Manual input is always possible as well.
"""

from imc.ahp import ahp
from imc.database import load_cities, save_cities


# Size classes (BBSR-style, the classification used for Konstanz in the thesis).
# Each entry: (lower limit, upper limit, name). None = no upper limit.
SIZE_CLASSES = [
    (0,       5_000,   "rural municipality"),
    (5_000,   20_000,  "small town"),
    (20_000,  100_000, "medium-sized town"),
    (100_000, None,    "large city"),
]


def size_class(population):
    """Return the size-class name of a population, e.g. 33743 -> 'medium-sized town'."""
    for low, high, name in SIZE_CLASSES:
        if population >= low and (high is None or population < high):
            return name


# The survey library uses the same JSON load/save as the city database,
# just with a different file. A survey is a dictionary like a city.
load_surveys = load_cities
save_surveys = save_cities


def add_survey(survey, path):
    """Add or replace a survey (matched by city name)."""
    surveys = load_surveys(path)
    surveys = [s for s in surveys if s["city"] != survey["city"]]
    surveys.append(survey)
    save_surveys(surveys, path)
    return surveys


def survey_weights(survey):
    """Run the AHP on a stored survey. Returns {criterion: weight} and the CR."""
    result = ahp(survey["matrix"])
    weights = dict(zip(survey["criteria"], (float(w) for w in result["weights"])))
    return weights, float(result["CR"])


def suggest_surveys(country, population, surveys, criteria):
    """Rank all stored surveys for a new city. Best suggestion first. Works for any number of criteria.

    country:    country code of the new city, e.g. "HU"
    population: population of the new city
    criteria:   the criteria the new city HAS INDICATORS FOR, e.g. ["cost", "comfort", "accessibility"]

    A survey is usable if it has a weight for every one of these criteria.
    Extra survey criteria (no indicator in this city) are dropped and the rest rescaled to 1,
    exactly as the thesis did with reliability.

    Returns a list of dictionaries: survey, tier (1-3, or None = unusable), label, reason, weights, CR.
    """
    my_class = size_class(population)
    suggestions = []

    for s in surveys:
        s_class = size_class(s["population"])
        same_country = s["country"] == country
        same_class = s_class == my_class
        diff = abs(s["population"] - population) / population   # relative difference, 0.25 = 25%

        # Reason in plain words, shown to the user next to the suggestion
        reason = (f"{s['country']}, {s_class}, population {s['population']:,} "
                  f"vs {population:,} ({diff:.0%} difference)")

        all_weights, CR = survey_weights(s)                      # AHP on the full survey
        missing = [c for c in criteria if c not in all_weights]  # criteria the survey can't weight
        extra = [c for c in all_weights if c not in criteria]    # survey criteria with no indicator

        if missing:
            tier, label = None, f"unusable: no weight for {', '.join(missing)}"
            weights = all_weights
        else:
            # Keep only the criteria this city uses, then rescale so they sum to 1
            kept = {c: all_weights[c] for c in criteria}
            total = sum(kept.values())
            weights = {c: w / total for c, w in kept.items()}

            if same_country and same_class:
                tier, label = 1, "recommended"
            elif same_class:
                tier, label = 2, "possible, check transferability"
            else:
                tier, label = 3, "not advised: different size class"
            if extra:
                label += f"; {', '.join(extra)} dropped (no indicator)"

        if CR >= 0.10:
            label += f" (warning: CR {CR:.1%} is above 10%)"

        suggestions.append({"survey": s, "tier": tier, "label": label, "reason": reason,
                            "weights": weights, "CR": CR, "diff": diff})

    # Sort: tier 1 first, then 2, then 3, unusable last; within a tier the closest population first.
    # A tuple sorts by its first item, and by the second only when the first ones are equal.
    suggestions.sort(key=lambda x: (x["tier"] if x["tier"] is not None else 99, x["diff"]))
    return suggestions


# Saaty scale for one pairwise question "A vs B":
# 9 = A extremely more important ... 1 = equal ... 1/9 = B extremely more important
SAATY = [9, 8, 7, 6, 5, 4, 3, 2, 1, 1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 6, 1 / 7, 1 / 8, 1 / 9]


def saaty_label(value, a, b):
    """Plain words for one slider position, e.g. 3 -> 'cost 3x more important'."""
    if value == 1:
        return "equal"
    if value > 1:
        return f"{a} {value:g}x more important"
    return f"{b} {1 / value:g}x more important"


def matrix_from_pairs(criteria, pairs):
    """Build the full AHP matrix from the upper-triangle answers.

    criteria: list of n names
    pairs:    {(i, j): value} for every i < j, value from SAATY ("criteria[i] vs criteria[j]")
    The diagonal is 1 and the lower triangle is filled with reciprocals (a_ji = 1 / a_ij),
    so the matrix is always consistent in that sense: the user answers each pair only once.
    """
    n = len(criteria)
    A = [[1.0] * n for _ in range(n)]
    for (i, j), v in pairs.items():
        A[i][j] = float(v)
        A[j][i] = 1.0 / float(v)
    return A


def manual_weights(weights):
    """Weights typed by the user, e.g. {"cost": 5, "comfort": 3, ...}.

    Any positive numbers are allowed; they are rescaled to sum to 1.
    """
    if any(w < 0 for w in weights.values()):
        raise ValueError("Weights can't be negative.")
    total = sum(weights.values())
    if total == 0:
        raise ValueError("At least one weight must be above zero.")
    return {name: w / total for name, w in weights.items()}