"""Saved calculations ("runs").

A run is a frozen copy of ONE calculation: every input, every intermediate result and the
calibration cities the model knew at that moment. Because the model learns, the same city gives a
different number after a new calibration city is stored - a run keeps what was predicted and why.

Runs are stored in data/runs.json (online: in the visitor's temporary folder) and can be
downloaded and loaded back as JSON files.
"""

import json
import math
from datetime import datetime
from pathlib import Path

from imc.compare import density_table

RUN_FORMAT = "imc-run/1"


def _num(v):
    """numpy / pandas numbers -> plain Python numbers; NaN -> None."""
    if v is None:
        return None
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _clean(obj):
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (str, bool)) or obj is None:
        return obj
    return _num(obj)


def make_run(result, label, weights, weight_source, forced, demo, version, cities_for_density=()):
    """Freeze a successful pipeline result into a plain, JSON-ready dictionary."""
    c, cascade, final = result["city"], result["cascade"], result["final"]
    fit = cascade.get("fit") or {}
    table = []
    for row in cascade["table"]:
        loo = row.get("loo") or {}
        table.append({"form": row["form"], "status": row["status"], "why": row.get("why", ""),
                      "params": (row.get("fit") or {}).get("params", {}),
                      "loo_median": loo.get("median"), "loo_max": loo.get("max"),
                      "score": row.get("score")})
    now = datetime.now()
    run = {
        "format": RUN_FORMAT,
        "id": now.strftime("%Y%m%d-%H%M%S-%f"),
        "label": label,
        "saved_at": now.isoformat(timespec="seconds"),
        "app_version": version,
        "demo": bool(demo),
        "city": {k: c.get(k) for k in ["name", "country", "P", "r_dmr", "a0", "w_cs", "u", "s", "N_max"]},
        "estimated": c.get("estimated", {}),
        "indicators": [{k: i.get(k) for k in ["code", "name", "group", "kind", "measured", "worst", "ideal"]}
                       for i in c.get("indicators", [])],
        "indicator_weights": result.get("indicator_weights", []),
        "weights": dict(weights),
        "weight_source": weight_source,
        "forced_form": forced,
        "result": {
            "N": final["N"], "N_rounded": round(final["N"]),
            "steps": [[label_, value] for label_, value in final["steps"]],
            "notes": list(final["notes"]),
            "Ci": result["Ci"], "R": result["R"],
            "form": cascade["form"], "params": fit.get("params", {}), "p": fit.get("p", []),
            "rho": fit.get("rho"), "R_range": list(cascade["R_range"]),
            "inside_range": bool(cascade.get("inside_range")),
            "alternatives": cascade["alternatives"],
            "cascade_table": table,
            "log": list(cascade["log"]),
        },
        "warnings": list(result.get("warnings", [])),
        "calibration_cities": [{k: x.get(k) for k in ["name", "country", "P", "r_dmr", "a0", "w_cs", "u", "s",
                                                    "R", "N_obs", "synthetic", "source"]}
                               for x in result["cal"]],
    }
    run["density"] = density_table(c["name"], c["P"], final["N"], c.get("u"), cities_for_density or result["cal"])
    return _clean(run)


# ---------------------------------------------------------------- storage
def load_runs(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_run(run, path):
    path = Path(path)
    runs = [r for r in load_runs(path) if r["id"] != run["id"]]
    runs.append(run)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(runs, f, indent=2, ensure_ascii=False)
    return runs


def delete_run(run_id, path):
    runs = [r for r in load_runs(path) if r["id"] != run_id]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(runs, f, indent=2, ensure_ascii=False)
    return runs


def to_json(run):
    return json.dumps(run, indent=2, ensure_ascii=False)


def from_json(text):
    """Read a downloaded run back. Raises ValueError if the file is not an IMC calculation."""
    try:
        run = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Not a JSON file: {error}") from None
    if not isinstance(run, dict) or run.get("format") != RUN_FORMAT:
        raise ValueError("This file is not a saved IMC calculation.")
    for key in ("id", "city", "result"):
        if key not in run:
            raise ValueError(f"The file is incomplete (missing '{key}').")
    return run


def file_stem(run):
    city = "".join(ch for ch in run["city"]["name"] if ch.isalnum() or ch in "-_") or "city"
    return f"IMC_{city}_{run['id'][:15]}"


def run_title(run):
    when = run["saved_at"].replace("T", " ")[:16]
    return f"{run['label']} · {when}" + (" · demo" if run.get("demo") else "")


# ---------------------------------------------------------------- comparison
ROWS = [  # (section, label, getter, format)
    ("City", "City", lambda r: r["city"]["name"], "s"),
    ("City", "Population P", lambda r: r["city"]["P"], ",.0f"),
    ("Inputs", "Daily mobility rate r_dmr", lambda r: r["city"]["r_dmr"], ".4f"),
    ("Inputs", "Licence, no car a0", lambda r: r["city"]["a0"], ".4f"),
    ("Inputs", "Willingness w_cs", lambda r: r["city"]["w_cs"], ".4f"),
    ("Inputs", "Users per vehicle u", lambda r: r["city"]["u"], ".1f"),
    ("Inputs", "Cycling share s", lambda r: r["city"].get("s"), ".2f"),
    ("Inputs", "Fleet cap N_max", lambda r: r["city"].get("N_max"), ".0f"),
    ("Inputs", "Weights from", lambda r: r.get("weight_source"), "s"),
    ("Evaluation", "Closeness Ci", lambda r: r["result"]["Ci"], ".3f"),
    ("Evaluation", "Deficiency R", lambda r: r["result"]["R"], ".3f"),
    ("Model", "Correction form", lambda r: r["result"]["form"], "s"),
    ("Model", "Calibration cities", lambda r: len(r["calibration_cities"]), "d"),
    ("Model", "Calibration factor rho", lambda r: r["result"]["rho"], ".3f"),
    ("Result", "Fleet size N", lambda r: r["result"]["N"], ".1f"),
    ("Result", "Vehicles per 1,000", lambda r: r["density"][0]["per_1000"], ".2f"),
    ("Result", "Daily users per 1,000", lambda r: r["density"][0]["users_per_1000"], ".2f"),
]


def _fmt(v, f):
    if v is None:
        return "—"
    if f == "s":
        return str(v)
    try:
        return format(v, f)
    except (TypeError, ValueError):
        return str(v)


def compare_table(runs):
    """Rows = quantities, columns = runs. Also returns which rows differ between the runs."""
    columns = [run_title(r) for r in runs]
    rows, differs = [], []
    for section, label, get, f in ROWS:
        values = []
        for r in runs:
            try:
                values.append(get(r))
            except (KeyError, IndexError, TypeError):
                values.append(None)
        rows.append({"section": section, "quantity": label, **{c: _fmt(v, f) for c, v in zip(columns, values)}})
        shown = {_fmt(v, f) for v in values}
        differs.append(len(shown) > 1)
    return rows, differs, columns


def changed_inputs(a, b):
    """Plain list of what differs between two runs of the same city ('u 8.4 -> 10.0')."""
    out = []
    for section, label, get, f in ROWS:
        if section not in ("Inputs", "City"):
            continue
        va, vb = _fmt(get(a), f), _fmt(get(b), f)
        if va != vb:
            out.append(f"{label}: {va} → {vb}")
    ia = {i["code"]: i for i in a.get("indicators", [])}
    ib = {i["code"]: i for i in b.get("indicators", [])}
    for code in sorted(set(ia) | set(ib)):
        if ia.get(code) != ib.get(code):
            out.append(f"Indicator {code} changed")
    if a.get("weights") != b.get("weights"):
        out.append("Criteria weights changed")
    return out


def city_as_run(city):
    """A stored database city in the same shape as a run, so it can sit in the comparison table."""
    N = city.get("N_obs")
    density = density_table(city["name"], city["P"], N or 0, city.get("u"), [])
    return {"id": f"db-{city['name']}", "label": f"{city['name']} (database" +
            (", observed fleet)" if N else ")"),
            "saved_at": city.get("saved", "") or "", "demo": False,
            "city": {k: city.get(k) for k in ["name", "country", "P", "r_dmr", "a0", "w_cs", "u", "s"]},
            "weight_source": "stored", "indicators": city.get("indicators", []), "weights": {},
            "result": {"Ci": city.get("Ci"), "R": city.get("R"), "form": "—", "rho": None,
                       "N": N, "R_range": [], "cascade_table": []},
            "calibration_cities": [],
            "density": density if N else [{"per_1000": None, "users_per_1000": None}]}
