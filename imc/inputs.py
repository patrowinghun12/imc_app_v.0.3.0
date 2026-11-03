"""Input checks and gap filling for one city.

validate_city -> (problems, warnings)
    problems: the calculation must NOT run (wrong value, swapped benchmarks, ...)
    warnings: the calculation can run, but the user should know
fill_gaps     -> missing optional values taken from the database (median), always flagged
"""

import statistics

from imc.surveys import size_class

U_PLAUSIBLE = (2, 30)   # users per vehicle per day; outside this range -> warning

# Values that are shares (fractions): must be between 0 and 1
FRACTIONS = ["r_dmr", "a0", "w_cs", "s"]

# Optional values: may be missing, then filled from the database.
# The cycling share s is NOT filled: guessing it would create a modal-split adjustment
# out of nothing. A missing s simply means "no modal-split adjustment".
OPTIONAL = ["r_dmr", "a0", "w_cs", "u"]

# Last resort when the database has no value either: the thesis baseline
THESIS_DEFAULTS = {"r_dmr": 0.60, "a0": 0.20, "w_cs": 0.3947, "u": 10}

NAMES = {"r_dmr": "daily mobility rate", "a0": "licence holders without a car",
         "w_cs": "willingness", "u": "users per vehicle per day", "s": "cycling share",
         "P": "population", "N_obs": "observed fleet", "N_max": "operator cap"}


def _check_number(city, key, problems, positive=True):
    """Check one number: is it a number, and positive if it must be."""
    v = city.get(key)
    if v is None:
        return
    if not isinstance(v, (int, float)):
        problems.append(f"{NAMES.get(key, key)} must be a number, got '{v}'.")
    elif positive and v <= 0:
        problems.append(f"{NAMES.get(key, key)} must be above 0, got {v}.")


def validate_city(city):
    """Check every input of a city. Returns (problems, warnings)."""
    problems, warnings = [], []

    # --- Required fields ---
    for key in ["name", "country", "P"]:
        if city.get(key) in (None, ""):
            problems.append(f"Missing required field: {NAMES.get(key, key)}.")
    _check_number(city, "P", problems)

    # --- Shares must be fractions; catch the classic "35 instead of 0.35" ---
    for key in FRACTIONS:
        v = city.get(key)
        if v is None or not isinstance(v, (int, float)):
            continue
        if 1 < v <= 100:
            problems.append(f"{NAMES[key]} = {v} looks like a percentage. "
                            f"Enter it as a fraction: {v / 100:g}, not {v}.")
        elif not 0 <= v <= 1:
            problems.append(f"{NAMES[key]} must be between 0 and 1, got {v}.")

    for key in ["u", "N_max"]:
        _check_number(city, key, problems)
    u = city.get("u")
    if isinstance(u, (int, float)) and u > 0 and not U_PLAUSIBLE[0] <= u <= U_PLAUSIBLE[1]:
        warnings.append(f"Users per vehicle u = {u} is unusual (typical {U_PLAUSIBLE[0]}-{U_PLAUSIBLE[1]}). "
                        f"The fleet scales with 1/u, so check it.")
    _check_number(city, "N_obs", problems, positive=False)
    if city.get("N_obs") is not None and city["N_obs"] < 0:
        problems.append("The observed fleet can't be negative.")

    # --- TOPSIS indicators: benchmark direction ---
    for ind in city.get("indicators", []):
        code, kind = ind["code"], ind["kind"]
        worst, ideal, measured = ind["worst"], ind["ideal"], ind["measured"]

        if worst == ideal:
            problems.append(f"{code}: worst and ideal benchmark are equal ({worst}).")
            continue
        # cost indicator (lower is better): ideal must be BELOW worst
        # benefit indicator (higher is better): ideal must be ABOVE worst
        if kind == "cost" and ideal > worst:
            problems.append(f"{code} is a cost indicator (lower is better), but its ideal ({ideal}) "
                            f"is above its worst case ({worst}). Are the benchmarks swapped?")
        elif kind == "benefit" and ideal < worst:
            problems.append(f"{code} is a benefit indicator (higher is better), but its ideal ({ideal}) "
                            f"is below its worst case ({worst}). Are the benchmarks swapped?")

        # Measured value beyond a benchmark: allowed, but worth a warning
        low, high = min(worst, ideal), max(worst, ideal)
        if not low <= measured <= high:
            side = "better than the ideal" if (measured < low) == (kind == "cost") else "worse than the worst case"
            warnings.append(f"{code}: measured value {measured} is {side} benchmark. "
                            f"TOPSIS still works, but check the value and the benchmarks.")

    return problems, warnings


def fill_gaps(city, db_cities):
    """Fill missing optional values from the database. Returns a NEW city dictionary.

    Priority: median of stored cities of the same country AND size class,
    then median of all stored cities, then the thesis default.
    Every filled value is recorded in city["estimated"] so the result can flag it.
    """
    filled = dict(city)
    filled["estimated"] = dict(city.get("estimated", {}))
    my_class = size_class(city["P"])

    similar = [c for c in db_cities
               if c.get("country") == city.get("country") and size_class(c["P"]) == my_class
               and c["name"] != city["name"]]
    others = [c for c in db_cities if c["name"] != city["name"]]
    calibration = [c for c in others if c.get("N_obs") is not None]

    for key in OPTIONAL:
        if filled.get(key) is not None:
            continue
        # u is an operating value: suggest the calibration cities' u first ("same utilisation")
        groups = [(similar, "same country and size class"), (others, "all stored cities")]
        if key == "u":
            groups = [(calibration, "same utilisation as the calibration cities")] + groups
        for group, label in groups:
            values = [c[key] for c in group if c.get(key) is not None]
            if values:
                filled[key] = statistics.median(values)
                filled["estimated"][key] = (f"median of {len(values)} "
                                            f"{'city' if len(values) == 1 else 'cities'} ({label})")
                break
        else:   # runs only if the loop above found nothing ("for ... else")
            if key in THESIS_DEFAULTS:
                filled[key] = THESIS_DEFAULTS[key]
                filled["estimated"][key] = "thesis default"

    return filled