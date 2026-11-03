"""Check subtask 2: does ahp() reproduce the thesis numbers?

Run with:  python check_ahp.py
"""

from imc.ahp import ahp

# Thesis Table 3.1 (Mosonmagyarovar). Order: Cost, Comfort, Reliability, Accessibility
criteria = ["Cost", "Comfort", "Reliability", "Accessibility"]
matrix = [
    [1,     2.507, 3.169, 2.914],
    [0.399, 1,     3.400, 3.414],
    [0.316, 0.294, 1,     2.563],
    [0.343, 0.293, 0.390, 1],
]

result = ahp(matrix)

# Print each weight next to its criterion name.
# zip() walks through two lists side by side.
for name, w in zip(criteria, result["weights"]):
    print(f"{name:<14} {w:.3f}")

print(f"lambda_max     {result['lambda_max']:.3f}")
print(f"CI             {result['CI']:.4f}")
print(f"CR             {result['CR']:.1%}")
print(f"consistent?    {result['consistent']}")

# Compare with the thesis: 0.448 / 0.303 / 0.152 / 0.097
expected = [0.448, 0.303, 0.152, 0.097]
# The thesis matrix is printed with only 3 decimals, so we allow a difference of 0.001.
ok = all(abs(w - e) <= 0.001 for w, e in zip(result["weights"], expected))
print("\nMATCHES THESIS" if ok else "\nDOES NOT MATCH THESIS")