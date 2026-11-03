"""Fleet density: vehicles and daily users per 1,000 inhabitants.

The estimate of one city is easier to judge next to other cities when it is scaled by population.
Two densities are shown:

  vehicles per 1,000 inhabitants  = 1000 * N / P
      what the operator has to buy; depends on the vehicle use u (N = demand / u)
  daily users per 1,000 inhabitants = 1000 * N * u / P
      the demand itself; for an estimate this equals 1000 * rho * T * f(R) / P,
      so it does NOT change when u is changed

A density comparison is a plausibility check, not a validation: cities differ in size,
public transport and operator strategy, so a different density is not an error by itself.
"""

import statistics


def per_1000(value, population):
    """Value per 1,000 inhabitants. None if the population is missing or not positive."""
    if value is None or not population or population <= 0:
        return None
    return 1000.0 * value / population


def _kind(city):
    if city.get("synthetic") or str(city.get("name", "")).startswith("Synthetic"):
        return "synthetic (demo)"
    return "observed"


def density_table(name, population, N_estimate, u, cities, references=()):
    """Rows for the comparison chart: this city first, then every city with a known fleet.

    name, population, N_estimate, u : the city just calculated
    cities     : database cities (or demo cities); only those with N_obs and P are used
    references : optional extra rows typed in by the user, each {"city", "per_1000"} -
                 e.g. published density values of other cities (their source is the user's)
    """
    rows = [{"city": name, "type": "this city (estimate)", "population": int(population),
             "vehicles": float(N_estimate),
             "per_1000": per_1000(N_estimate, population),
             "users_per_1000": per_1000(N_estimate * u, population) if u else None}]
    for c in cities:
        if c.get("N_obs") is None or not c.get("P") or c["name"] == name:
            continue
        rows.append({"city": c["name"], "type": _kind(c), "population": int(c["P"]),
                     "vehicles": float(c["N_obs"]),
                     "per_1000": per_1000(c["N_obs"], c["P"]),
                     "users_per_1000": per_1000(c["N_obs"] * c["u"], c["P"]) if c.get("u") else None})
    for r in references:
        try:
            value = float(r.get("per_1000"))
        except (TypeError, ValueError):
            continue
        label = str(r.get("city") or "").strip()
        if label and value > 0:
            rows.append({"city": label, "type": "reference (entered)", "population": None,
                         "vehicles": None, "per_1000": value, "users_per_1000": None})
    return rows


def summary(rows):
    """Where the estimate sits relative to the observed cities (median and ratio)."""
    est = rows[0]["per_1000"]
    observed = [r["per_1000"] for r in rows[1:] if r["type"] == "observed"]
    if not observed or est is None:
        return None
    med = statistics.median(observed)
    return {"estimate": est, "median_observed": med, "ratio": est / med, "n": len(observed)}
