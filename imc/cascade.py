"""Selection cascade: choose the correction form, then predict the fleet.

Follows the program flowchart:
  1. Form forced by the user?    -> use it, but still report its leave-one-out error
  2. Fewer than 3 cal. cities?   -> quadratic + pooled eta, with a warning
  3. Otherwise, for each form (quadratic -> log -> power -> saturation):
       fit on all cities -> parameters plausible? -> leave-one-out error <= threshold?
       passed -> candidate
  4. Pick the candidate with the lowest PENALISED error (extra parameters cost points).
     No candidate -> lowest error anyway, flagged.

Every step writes a plain-language line to `log`; the GUI and the visual walk-through
(subtask 9b) show these lines.
"""

import statistics

from imc.correction import FORMS, CASCADE_ORDER
from imc.fitting import fit_form, predict_with_fit

LOO_THRESHOLD = 0.25      # a form passes if its median leave-one-out error is at most 25%
PENALTY_PER_PARAM = 0.02  # each shape parameter adds 2 percentage points to the error
MIN_CITIES = 3            # below this, the forms can't be compared


def leave_one_out(name, cal_cities):
    """Hide each city in turn, fit on the others, predict the hidden one.

    Returns the median and max percentage error, the error of every city,
    or None if the form can't be fitted on the smaller sets.
    """
    errors = {}
    for hidden in cal_cities:
        others = [c for c in cal_cities if c is not hidden]       # everyone except the hidden city
        fit = fit_form(name, others)
        if not fit["ok"]:
            return None
        predicted = predict_with_fit(hidden, fit)
        errors[hidden["name"]] = abs(predicted - hidden["N_obs"]) / hidden["N_obs"]
    return {"median": statistics.median(errors.values()),
            "max": max(errors.values()),
            "per_city": errors}


def run_cascade(city, cal_cities, forced=None,
                threshold=LOO_THRESHOLD, penalty=PENALTY_PER_PARAM):
    """Choose a form and predict the fleet of `city`. Returns a dictionary (see the end)."""
    log = []
    warnings = []
    table = []                      # one row per form, for the GUI

    n = len(cal_cities)
    log.append(f"{n} calibration {'city' if n == 1 else 'cities'}: "
               f"{', '.join(c['name'] for c in cal_cities)}")

    # ---- 2) Too few cities: no comparison possible ----
    if n < MIN_CITIES and forced is None:
        log.append(f"Fewer than {MIN_CITIES} cities: forms can't be compared, using the quadratic.")
        warnings.append(f"Only {n} calibration {'city' if n == 1 else 'cities'}: the curve shape is "
                        f"assumed (thesis quadratic), not tested.")
        chosen = fit_form("quadratic", cal_cities)
        table.append({"form": "quadratic", "status": "used (too few cities to compare)", "fit": chosen})

    else:
        # ---- 3) Test every form ----
        candidates = []
        for name in CASCADE_ORDER:
            n_params = len(FORMS[name]["params"])
            log.append(f"Testing {name} ({FORMS[name]['about']}, {n_params} parameter(s))")

            fit = fit_form(name, cal_cities)
            if not fit["ok"]:
                log.append(f"  rejected: {fit['reason']}")
                table.append({"form": name, "status": "rejected", "why": fit["reason"]})
                continue

            if fit["at_limit"]:
                why = f"parameter {', '.join(fit['at_limit'])} at the edge of its plausible range"
                log.append(f"  rejected: {why}")
                table.append({"form": name, "status": "rejected", "why": why, "fit": fit})
                continue

            loo = leave_one_out(name, cal_cities)
            if loo is None:
                why = "too few cities for leave-one-out"
                log.append(f"  rejected: {why}")
                table.append({"form": name, "status": "rejected", "why": why, "fit": fit})
                continue

            score = loo["median"] + penalty * n_params
            row = {"form": name, "fit": fit, "loo": loo, "score": score}
            if loo["median"] <= threshold:
                log.append(f"  passed: leave-one-out error {loo['median']:.1%} "
                           f"(+{penalty * n_params:.0%} penalty = {score:.1%})")
                row["status"] = "candidate"
                candidates.append(row)
            else:
                log.append(f"  rejected: leave-one-out error {loo['median']:.1%} "
                           f"is above {threshold:.0%}")
                row["status"] = "rejected"
                row["why"] = f"leave-one-out {loo['median']:.1%} > {threshold:.0%}"
            table.append(row)

        tested = [r for r in table if "score" in r]       # forms that got a leave-one-out error

        # ---- 1) Forced form: use it, but still show how good it is ----
        if forced is not None:
            row = next(r for r in table if r["form"] == forced)
            chosen = row.get("fit") or fit_form(forced, cal_cities)
            if not chosen["ok"]:
                raise ValueError(f"The forced form '{forced}' can't be fitted: {chosen['reason']}")
            log.append(f"Form forced by the user: {forced}.")
            if "loo" in row:
                warnings.append(f"'{forced}' was chosen by hand. Its leave-one-out error is "
                                f"{row['loo']['median']:.1%}.")
            else:
                warnings.append(f"'{forced}' was chosen by hand. It has no leave-one-out error "
                                f"({row.get('why', 'too few cities')}).")

        # ---- 4) Pick the best candidate ----
        elif candidates:
            best = min(candidates, key=lambda r: r["score"])
            chosen = best["fit"]
            best["status"] = "chosen"
            log.append(f"Chosen: {best['form']} (lowest penalised error {best['score']:.1%}).")

        elif tested:
            best = min(tested, key=lambda r: r["score"])
            chosen = best["fit"]
            best["status"] = "chosen (none passed)"
            log.append(f"No form passed. Using {best['form']}, the least bad one.")
            warnings.append(f"No correction form passed the {threshold:.0%} leave-one-out test; "
                            f"'{best['form']}' is the least bad. Treat the result with caution.")
        else:
            chosen = fit_form("quadratic", cal_cities)
            log.append("No form could be tested. Using the quadratic.")
            warnings.append("No form could be tested; the quadratic is assumed.")

    # ---- Prediction ----
    N = predict_with_fit(city, chosen)
    log.append(f"Predicted fleet for {city['name']}: {N:.1f} vehicles.")

    # Is the new city's R inside the R range the curve was fitted on?
    lo, hi = chosen["R_range"]
    inside = lo <= city["R"] <= hi
    if not inside:
        msg = (f"R = {city['R']:.3f} is outside the range the curve was fitted on "
               f"({lo:.3f}-{hi:.3f}): the result is an extrapolation.")
        log.append(msg)
        warnings.append(msg)

    # How much do the forms that could be fitted disagree for this city? (a rough uncertainty)
    alternatives = {r["form"]: predict_with_fit(city, r["fit"])
                    for r in table if r.get("fit") is not None and r["fit"]["ok"]}

    return {
        "form": chosen["name"],
        "fit": chosen,
        "N": N,
        "R": city["R"],
        "R_range": (lo, hi),
        "inside_range": inside,
        "alternatives": alternatives,
        "table": table,
        "log": log,
        "warnings": warnings,
    }
