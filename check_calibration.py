"""Check subtask 5: store cities in the database, learn from Konstanz, predict Mosonmagyarovar.

Targets: rho = 0.6074 (Konstanz), Mosonmagyarovar = 18.2 vehicles.

Run with:  python check_calibration.py
"""

from pathlib import Path

from imc.ahp import ahp
from imc.topsis import indicator_weights, topsis
from imc.database import add_city, load_cities, calibration_cities
from imc.calibration import rho_for_city, pooled_rho, predict_fleet

# --- R for both cities: same AHP + TOPSIS as subtasks 2-3 ---
matrix = [
    [1,     2.507, 3.169, 2.914],
    [0.399, 1,     3.400, 3.414],
    [0.316, 0.294, 1,     2.563],
    [0.343, 0.293, 0.390, 1],
]
w = ahp(matrix)["weights"]
gw = {"cost": w[0], "comfort": w[1], "reliability": w[2], "accessibility": w[3]}
weights = indicator_weights(gw, ["comfort", "cost", "cost", "accessibility", "accessibility"])

ppp = 247.6
R_k = topsis([1.90, 2.60 / 21.8, 50.75 / 44, 2.19, 25.5],
             [5, 40 / ppp, 1.50, 0.8, 60], [1, 20 / ppp, 0.50, 2.4, 20], weights)["R"]
R_m = topsis([1.73, 26.39, 71.59, 1.9, 35],
             [5, 40, 120, 0.8, 60], [1, 20, 40, 2.4, 20], weights)["R"]

# --- Two cities as dictionaries. Konstanz has N_obs, so it is a calibration city. ---
konstanz = {"name": "Konstanz", "country": "DE", "P": 86323, "r_dmr": 0.60, "a0": 0.24,
            "w_cs": 0.3947, "u": 8.4, "R": round(R_k, 4), "N_obs": 74}
moson = {"name": "Mosonmagyarovar", "country": "HU", "P": 33743, "r_dmr": 0.60, "a0": 0.20,
         "w_cs": 0.3947, "u": 8.4, "R": round(R_m, 4), "N_obs": None}

# --- Store them in a separate check database, so the real one stays clean ---
db = Path("data/cities_check.json")
if db.exists():
    db.unlink()                      # start from an empty file every time this check runs
add_city(konstanz, db)
add_city(moson, db)

cities = load_cities(db)             # read back from the file, as the app will do
print(f"Cities in database: {[c['name'] for c in cities]}")
cal = calibration_cities(cities)
print(f"Calibration cities: {[c['name'] for c in cal]}")

# --- Learn from Konstanz ---
rho_k = rho_for_city(cities[0])          # rho is transferred between cities; u belongs to each city
print(f"\nKonstanz: rho = {rho_k:.4f}  (thesis 0.6074)  "
      f"{'OK' if abs(rho_k - 0.6074) < 0.0005 else 'WRONG'}")

# --- Predict Mosonmagyarovar with what was learnt ---
rho = pooled_rho(cal)
N_m = predict_fleet(cities[1], rho)
print(f"Mosonmagyarovar: N = {N_m:.1f}  (thesis 18.2)  {'OK' if round(N_m, 1) == 18.2 else 'WRONG'}")

print(f"\nOpen {db} to see what was stored.")