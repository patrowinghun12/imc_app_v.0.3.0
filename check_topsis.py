"""Check subtask 3: does topsis() reproduce Ci 0.747 (Mosonmagyarovar) and 0.653 (Konstanz)?

Run with:  python check_topsis.py
"""

from imc.ahp import ahp
from imc.topsis import indicator_weights, topsis

# --- Step 1: AHP group weights (same matrix as subtask 2) ---
matrix = [
    [1,     2.507, 3.169, 2.914],
    [0.399, 1,     3.400, 3.414],
    [0.316, 0.294, 1,     2.563],
    [0.343, 0.293, 0.390, 1],
]
w = ahp(matrix)["weights"]
group_weights = {"cost": w[0], "comfort": w[1], "reliability": w[2], "accessibility": w[3]}

# --- Step 2: one weight per indicator (reliability has no indicator, so it drops out) ---
#            C1 crowding, C2 cost/min, C3 monthly/trip, C4 stop density, C5 headway
groups = ["comfort", "cost", "cost", "accessibility", "accessibility"]
weights = indicator_weights(group_weights, groups)
print("Indicator weights:", [round(float(x), 3) for x in weights])   # thesis: 0.357 0.264 0.264 0.057 0.057

# --- Step 3: Mosonmagyarovar (HUF) ---
moson = topsis(
    measured=[1.73, 26.39, 71.59, 1.9, 35],
    worst=   [5,    40,    120,   0.8, 60],
    ideal=   [1,    20,    40,    2.4, 20],
    weights=weights,
)

# --- Step 4: Konstanz (EUR). C2 benchmarks = Hungarian 40 / 20 HUF converted with PPP 247.6 ---
ppp = 247.6
konstanz = topsis(
    measured=[1.90, 2.60 / 21.8,  50.75 / 44, 2.19, 25.5],
    worst=   [5,    40 / ppp,     1.50,       0.8,  60],
    ideal=   [1,    20 / ppp,     0.50,       2.4,  20],
    weights=weights,
)

for name, res, expected in [("Mosonmagyarovar", moson, 0.747), ("Konstanz", konstanz, 0.653)]:
    ok = abs(res["Ci"] - expected) <= 0.001
    print(f"{name:<16} Ci = {res['Ci']:.3f}  R = {res['R']:.3f}  "
          f"D+ = {res['D_plus']:.3f}  D- = {res['D_minus']:.3f}  "
          f"(thesis {expected})  {'OK' if ok else 'WRONG'}")