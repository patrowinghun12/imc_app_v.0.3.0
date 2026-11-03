"""First-run data: the real thesis cities and survey, written to the database if it is empty."""

from imc.database import load_cities, save_cities
from imc.surveys import load_surveys, save_surveys
from imc.pipeline import compute_R
from imc.ahp import ahp

CRITERIA = ["cost", "comfort", "reliability", "accessibility"]
MOSON_MATRIX = [[1,     2.507, 3.169, 2.914],
                [0.399, 1,     3.400, 3.414],
                [0.316, 0.294, 1,     2.563],
                [0.343, 0.293, 0.390, 1]]

MOSON_SURVEY = {"city": "Mosonmagyarovar", "country": "HU", "population": 33743,
                "criteria": CRITERIA, "respondents": 71, "matrix": MOSON_MATRIX}

KONSTANZ_INDICATORS = [   # EUR; C2 benchmarks = 40 / 20 HUF converted with PPP 247.6
    {"code": "C1", "name": "Crowding", "group": "comfort", "kind": "cost",
     "measured": 1.90, "worst": 5, "ideal": 1},
    {"code": "C2", "name": "Cost per minute", "group": "cost", "kind": "cost",
     "measured": 2.60 / 21.8, "worst": 40 / 247.6, "ideal": 20 / 247.6},
    {"code": "C3", "name": "Monthly pass per trip", "group": "cost", "kind": "cost",
     "measured": 50.75 / 44, "worst": 1.50, "ideal": 0.50},
    {"code": "C4", "name": "Stop density", "group": "accessibility", "kind": "benefit",
     "measured": 2.19, "worst": 0.8, "ideal": 2.4},
    {"code": "C5", "name": "Headway", "group": "accessibility", "kind": "cost",
     "measured": 25.5, "worst": 60, "ideal": 20},
]


def seed(cities_path, surveys_path):
    """Write Konstanz and the Mosonmagyarovar survey if the files are empty.

    Also repairs an older Konstanz record that was saved without its indicators:
    they are needed to re-score Konstanz whenever the weights change.
    """
    if not load_surveys(surveys_path):
        save_surveys([MOSON_SURVEY], surveys_path)

    cities = load_cities(cities_path)
    for c in cities:
        if c["name"] == "Konstanz" and not c.get("indicators"):
            c["indicators"] = KONSTANZ_INDICATORS
            save_cities(cities, cities_path)

    if not cities:
        w = ahp(MOSON_MATRIX)["weights"]
        group_weights = dict(zip(CRITERIA, (float(x) for x in w)))
        R = compute_R(KONSTANZ_INDICATORS, group_weights)[0]["R"]
        konstanz = {"name": "Konstanz", "country": "DE", "P": 86323, "r_dmr": 0.60, "a0": 0.24,
                    "w_cs": 0.3947, "u": 8.4, "R": float(R), "N_obs": 74, "s": 0.34,
                    "indicators": KONSTANZ_INDICATORS,
                    "source": "TDK2: operator data [28], consultation (J. Everling, S. Fischer)"}
        save_cities([konstanz], cities_path)