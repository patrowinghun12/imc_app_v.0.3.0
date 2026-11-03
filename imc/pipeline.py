"""The whole model in one call: inputs -> checks -> AHP/TOPSIS -> cascade -> adjustments.

The app only collects inputs and shows this result; all the maths lives here,
so it can be tested without the interface.
"""

from datetime import date

from imc.topsis import indicator_weights, topsis
from imc.inputs import validate_city, fill_gaps
from imc.database import calibration_cities
from imc.cascade import run_cascade
from imc.adjustments import final_fleet


def compute_R(indicators, group_weights):
    """TOPSIS for one city. indicators: list of dicts with group, measured, worst, ideal."""
    weights = indicator_weights(group_weights, [i["group"] for i in indicators])
    res = topsis(measured=[i["measured"] for i in indicators],
                 worst=[i["worst"] for i in indicators],
                 ideal=[i["ideal"] for i in indicators],
                 weights=weights)
    return res, weights


def predict(city, indicators, group_weights, db_cities, forced=None):
    """Run the full model for one city. Returns a dictionary; 'ok' is False if it can't run."""
    city = dict(city, indicators=indicators)

    # 1) Input checks: stop on any problem
    problems, warnings = validate_city(city)
    groups = {i["group"] for i in indicators}
    missing = [g for g in groups if g not in group_weights]
    if missing:
        problems.append(f"No weight for criterion: {', '.join(missing)}.")
    if not indicators:
        problems.append("Add at least one indicator.")
    if problems:
        return {"ok": False, "problems": problems, "warnings": warnings}

    # 2) Gap filling from the database
    filled = fill_gaps(city, db_cities)

    # 3) TOPSIS -> R
    topsis_res, ind_weights = compute_R(indicators, group_weights)
    filled["R"] = topsis_res["R"]

    # 4) Calibration cities (never the city itself), re-scored with the SAME weights.
    #    Their R must be measured with the same ruler as the new city's R; otherwise a change of
    #    weights would compare two cities scored in different ways.
    cal = []
    for c in calibration_cities(db_cities):
        if c["name"] == city["name"]:
            continue
        c_groups = {i["group"] for i in c.get("indicators", [])}
        if c_groups and c_groups <= set(group_weights):
            c = dict(c, R=float(compute_R(c["indicators"], group_weights)[0]["R"]))
        elif not c.get("synthetic"):              # demo cities are defined by R itself
            warnings.append(f"{c['name']}: its R could not be recomputed with these weights "
                            f"(no stored indicators, or a criterion without weight); its stored R is used.")
        cal.append(c)
    if not cal:
        return {"ok": False, "warnings": warnings,
                "problems": ["The database has no calibration city (a city with an observed fleet)."]}

    # 5) Cascade + 6) adjustments
    cascade = run_cascade(filled, cal, forced=None if forced == "automatic" else forced)
    final = final_fleet(cascade["N"], filled, cal)

    return {
        "ok": True,
        "city": filled,
        "Ci": topsis_res["Ci"], "R": topsis_res["R"],
        "indicator_weights": [float(w) for w in ind_weights],
        "cascade": cascade,
        "cal": cal,
        "final": final,
        "warnings": warnings + cascade["warnings"],
        "estimated": filled.get("estimated", {}),
    }


def make_record(result, N_obs=None, source=""):
    """Turn a successful result into a city record for the database.

    If the real fleet N_obs is given, the record also keeps the model's prediction made
    BEFORE it saw that fleet. That is an honest out-of-sample test of the model.
    """
    c = result["city"]
    record = {key: c.get(key) for key in ["name", "country", "P", "r_dmr", "a0", "w_cs", "u", "s"]}
    record.update({
        "R": float(result["R"]),
        "Ci": float(result["Ci"]),
        "indicators": c["indicators"],
        "estimated": c.get("estimated", {}),
        "N_obs": N_obs,
        "source": source,
        "saved": date.today().isoformat(),
    })
    if N_obs is not None:
        predicted = result["final"]["N"]
        record["test_before_learning"] = {
            "predicted": round(float(predicted), 2),
            "observed": N_obs,
            "error": round(abs(predicted - N_obs) / N_obs, 4),
            "form": result["cascade"]["form"],
            "calibration_cities": [x["name"] for x in result["cal"]],
        }
    return record