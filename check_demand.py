"""Check subtask 4: forward run of the thesis model.

Targets: Konstanz 85 (baseline parameters) and 122 (measured parameters),
         Mosonmagyarovar 28 (TDK1, published Ci 0.706).

Run with:  python check_demand.py
"""

from imc.ahp import ahp
from imc.topsis import indicator_weights, topsis
from imc.correction import quadratic
from imc.demand import interested_people, fleet_size

# --- AHP -> indicator weights -> TOPSIS for Konstanz (same as subtask 3) ---
matrix = [
    [1,     2.507, 3.169, 2.914],
    [0.399, 1,     3.400, 3.414],
    [0.316, 0.294, 1,     2.563],
    [0.343, 0.293, 0.390, 1],
]
w = ahp(matrix)["weights"]
group_weights = {"cost": w[0], "comfort": w[1], "reliability": w[2], "accessibility": w[3]}
weights = indicator_weights(group_weights, ["comfort", "cost", "cost", "accessibility", "accessibility"])

ppp = 247.6
R_konstanz = topsis(
    measured=[1.90, 2.60 / 21.8, 50.75 / 44, 2.19, 25.5],
    worst=   [5,    40 / ppp,    1.50,       0.8,  60],
    ideal=   [1,    20 / ppp,    0.50,       2.4,  20],
    weights=weights,
)["R"]

f = quadratic(R_konstanz)
print(f"Konstanz: R = {R_konstanz:.3f}, f(R) = {f:.3f}")      # thesis: 0.347, 0.209


def run(label, P, r_dmr, a0, w_cs, u, f, expected):
    """Do one forward run and print it next to the thesis value."""
    T = interested_people(P, r_dmr, a0, w_cs)
    N = fleet_size(T, f, u)
    ok = round(N) == expected
    print(f"{label:<34} T = {T:,.0f}  users/day = {T * f:,.0f}  N = {N:.1f}  "
          f"(thesis {expected})  {'OK' if ok else 'WRONG'}")


# Konstanz with the old (baseline) assumptions: a0 = 0.20, u = 10
run("Konstanz, baseline parameters", P=86323, r_dmr=0.60, a0=0.20, w_cs=0.3947, u=10,  f=f, expected=85)

# Konstanz with the values measured there: a0 = 0.24, u = 8.4
run("Konstanz, measured parameters", P=86323, r_dmr=0.60, a0=0.24, w_cs=0.3947, u=8.4, f=f, expected=122)

# Mosonmagyarovar as published in TDK1 (Ci 0.706 -> R 0.294)
run("Mosonmagyarovar, TDK1 (Ci 0.706)", P=33743, r_dmr=0.60, a0=0.20, w_cs=0.3947, u=10,
    f=quadratic(1 - 0.747), expected=28)

print("\nObserved Konstanz fleet: 74")