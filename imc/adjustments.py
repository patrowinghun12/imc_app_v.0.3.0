"""Adjustments applied AFTER the cascade's fleet estimate.

1. Modal split (cycling share s), RELATIVE to the calibration cities:
       N  x  (1 - s_new) / (1 - s_ref)
   eta was learnt from cities that already have their own cycling share, so an absolute
   factor (1 - s_new) would count their cycling twice. Only the DIFFERENCE is applied.
   s_ref = geometric mean of (1 - s) over the calibration cities.

2. Operator cap: N = min(N, N_max). A supply limit, kept apart from the demand model.
"""

import math


def modal_split_factor(city, cal_cities):
    """Returns (factor, note). factor = 1 means no adjustment."""
    if city.get("s") is None:
        return 1.0, "No cycling share given for this city: no modal-split adjustment."

    missing = [c["name"] for c in cal_cities if c.get("s") is None]
    if missing:
        return 1.0, (f"No cycling share for calibration {'city' if len(missing) == 1 else 'cities'} "
                     f"{', '.join(missing)}: no modal-split adjustment.")

    logs = [math.log(1 - c["s"]) for c in cal_cities]
    ref = math.exp(sum(logs) / len(logs))          # geometric mean of (1 - s)
    factor = (1 - city["s"]) / ref
    return factor, (f"Cycling share {city['s']:.0%} vs {1 - ref:.0%} in the calibration "
                    f"{'city' if len(cal_cities) == 1 else 'cities'}: fleet x {factor:.3f}.")


def final_fleet(N_model, city, cal_cities):
    """Apply modal split, then the operator cap. Returns the steps, for the result screen."""
    steps = [("Model estimate (cascade)", N_model)]
    notes = []

    factor, note = modal_split_factor(city, cal_cities)
    notes.append(note)
    N = N_model * factor
    if factor != 1.0:
        steps.append(("After modal-split adjustment", N))

    N_max = city.get("N_max")
    if N_max is not None and N > N_max:
        notes.append(f"Capped at the operator's maximum of {N_max} vehicles "
                     f"(demand estimate was {N:.1f}).")
        N = N_max
        steps.append(("After operator cap", N))

    return {"N": N, "steps": steps, "notes": notes}