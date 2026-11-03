"""Check the density comparison (vehicles and daily users per 1,000 inhabitants).

Run with:  python check_compare.py
"""

from imc.compare import per_1000, density_table, summary
from imc.demo import synthetic_cities

ok_all = True


def check(label, ok, detail=""):
    global ok_all
    ok_all &= bool(ok)
    print(f"{'OK  ' if ok else 'FAIL'}   {label:<55} {detail}")


konstanz = {"name": "Konstanz", "P": 86323, "N_obs": 74, "u": 8.4}

check("Konstanz: 74 / 86,323 -> 0.857 per 1,000", round(per_1000(74, 86323), 3) == 0.857, per_1000(74, 86323))
check("no population -> None", per_1000(10, 0) is None)

rows = density_table("Mosonmagyaróvár", 33743, 18.2, 8.4, [konstanz])
check("this city first", rows[0]["type"] == "this city (estimate)")
check("Mosonmagyaróvár: 18.2 -> 0.539 per 1,000", round(rows[0]["per_1000"], 3) == 0.539, rows[0]["per_1000"])
check("users per 1,000 = vehicles x u", abs(rows[0]["users_per_1000"] - 0.539 * 8.4) < 0.01, rows[0]["users_per_1000"])

# daily users per 1,000 must not depend on u: N = demand / u, so N * u is constant
a = density_table("X", 33743, 152.9 / 8.4, 8.4, [])[0]["users_per_1000"]
b = density_table("X", 33743, 152.9 / 12, 12, [])[0]["users_per_1000"]
check("users per 1,000 independent of u", abs(a - b) < 1e-9, f"{a:.3f} = {b:.3f}")

s = summary(rows)
check("estimate / Konstanz density = 0.63", round(s["ratio"], 2) == 0.63, s["ratio"])

demo = density_table("X", 30000, 10, 10, synthetic_cities())
check("demo cities marked synthetic", all(r["type"] == "synthetic (demo)" for r in demo[1:]), len(demo) - 1)
check("synthetic cities not in the observed median", summary(demo) is None)

ref = density_table("X", 30000, 10, 10, [], [{"city": "Reference A", "per_1000": "1.2"}, {"city": "", "per_1000": 3},
                                            {"city": "Bad", "per_1000": "abc"}])
check("only valid reference rows kept", [r["city"] for r in ref[1:]] == ["Reference A"])

print("\nAll density checks passed." if ok_all else "\nSOME DENSITY CHECKS FAILED.")
