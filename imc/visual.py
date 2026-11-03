"""Visual walk-through of the cascade (subtask 9b).

build_frames() turns a cascade result into a list of animation frames.
draw_frame()   draws one frame as an Altair chart.
The app plays the frames one after another; a slider can also show any single frame.

What a frame shows:
  - every form tested so far, coloured by its state (testing / passed / rejected / chosen)
  - the calibration cities as dots (where they sit on the curve being tested)
  - a "crosshair": from the city's R on the x-axis UP to the curve, then ACROSS to the y-axis,
    where the corrected value f(R) is written
"""

import altair as alt
import pandas as pd

from imc.correction import FORMS, CASCADE_ORDER
from imc.demand import interested_people

# colour, line width, dash pattern ([] = solid) for each state
STYLE = {
    "testing":   ("#1f77b4", 3.0, []),
    "candidate": ("#ff7f0e", 2.0, []),
    "rejected":  ("#b0b0b0", 1.5, [6, 4]),
    "chosen":    ("#2ca02c", 4.0, []),
}
LEGEND = "Blue = being tested · orange = passed · grey dashed = rejected · green = chosen"

# crosshair progress: 0 -> 1 climbs up to the curve, 1 -> 2 runs across to the y-axis
CLIMB = [0.25, 0.5, 0.75, 1.0, 1.33, 1.66, 2.0]


def build_frames(cascade, city_name):
    """List of frames. Each frame: states {form: state}, focus form, progress, message."""
    frames = []
    states = {}
    R = cascade["R"]
    rows = {row["form"]: row for row in cascade["table"]}

    for name in CASCADE_ORDER:
        row = rows.get(name)
        if row is None:                                   # never tested (fewer than 3 cities)
            frames.append({"states": dict(states), "focus": None, "progress": 0,
                           "message": f"**{name}**: not tested - fewer than 3 calibration cities, "
                                      f"so the forms can't be compared."})
            continue

        fit = row.get("fit")
        if fit is None or not fit["ok"]:                  # couldn't even be fitted
            frames.append({"states": dict(states), "focus": None, "progress": 0,
                           "message": f"**{name}**: rejected - {row.get('why', 'could not be fitted')}."})
            continue

        # 1) animate: climb from R up to the curve, then across to f(R)
        testing = dict(states, **{name: "testing"})
        for p in CLIMB:
            frames.append({"states": testing, "focus": name, "progress": p,
                           "message": f"Testing **{name}** ({FORMS[name]['about']}): "
                                      f"R = {R:.3f} -> up to the curve -> across to f(R)"})

        # 2) verdict
        if row["status"] == "rejected":
            states[name] = "rejected"
            msg = f"**{name}** rejected: {row['why']}."
        else:
            states[name] = "candidate"
            if "loo" in row:
                msg = (f"**{name}** passed: leave-one-out error {row['loo']['median']:.1%}, "
                       f"with penalty {row['score']:.1%}.")
            else:
                msg = f"**{name}** used: fewer than 3 calibration cities, nothing to compare it with."
        frames.append({"states": dict(states), "focus": name, "progress": 2.0, "message": msg})

    # 3) final frame: the chosen form
    chosen = cascade["form"]
    states[chosen] = "chosen"
    f_value = FORMS[chosen]["f"](R, cascade["fit"]["p"])
    frames.append({"states": dict(states), "focus": chosen, "progress": 2.0, "final": True,
                   "message": f"Chosen: **{chosen}**. For {city_name}, f(R) = {f_value:.3f} "
                              f"-> model estimate **{cascade['N']:.1f} vehicles**."})
    return frames


def _curve(name, fit):
    grid = [i / 200 for i in range(201)]
    return pd.DataFrame({"R": grid, "f": [FORMS[name]["f"](r, fit["p"]) for r in grid]})


def draw_frame(frame, cascade, cal_cities, height=420):
    """Draw one frame. Returns an Altair chart."""
    R = cascade["R"]
    fits = {row["form"]: row["fit"] for row in cascade["table"]
            if row.get("fit") is not None and row["fit"]["ok"]}
    x = alt.X("R:Q", title="R  (0 = ideal public transport, 1 = worst)", scale=alt.Scale(domain=[0, 1]))
    y = alt.Y("f:Q", title="correction f(R)", scale=alt.Scale(domain=[0, 1]))
    layers = []

    # shaded R range of the calibration cities (where the curves are backed by data)
    lo, hi = cascade["R_range"]
    layers.append(alt.Chart(pd.DataFrame({"R": [lo], "R2": [max(hi, lo + 0.006)]}))
                  .mark_rect(opacity=0.12, color="#1f77b4").encode(x=x, x2="R2:Q"))

    # one line per form that has a state; draw rejected first so the others sit on top
    order = sorted(frame["states"].items(), key=lambda kv: kv[1] != "rejected")
    for name, state in order:
        if name not in fits:
            continue
        colour, width, dash = STYLE[state]
        layers.append(alt.Chart(_curve(name, fits[name]))
                      .mark_line(color=colour, strokeWidth=width, strokeDash=dash).encode(x=x, y=y))

    focus = frame["focus"]
    if focus in fits:
        fit = fits[focus]
        f_R = FORMS[focus]["f"](R, fit["p"])
        colour = STYLE[frame["states"].get(focus, "testing")][0]

        # calibration cities as dots: where each city lies on the focus curve's scale
        pts = []
        for c in cal_cities:
            T = interested_people(c["P"], c["r_dmr"], c["a0"], c["w_cs"])
            pts.append({"R": c["R"], "f": c["N_obs"] * c["u"] / (fit["rho"] * T), "city": c["name"]})
        layers.append(alt.Chart(pd.DataFrame(pts)).mark_point(size=70, filled=True, color="black",
                                                              opacity=0.7)
                      .encode(x=x, y=y, tooltip=["city:N", "R:Q", "f:Q"]))

        # crosshair: up from the x-axis, then across to the y-axis
        p = frame["progress"]
        up_to = f_R * min(p, 1.0)
        layers.append(alt.Chart(pd.DataFrame({"R": [R], "y0": [0.0], "y1": [up_to]}))
                      .mark_rule(color="red", strokeWidth=2.5)
                      .encode(x=x, y=alt.Y("y0:Q", scale=alt.Scale(domain=[0, 1])), y2="y1:Q"))
        if p > 1.0:
            left = R - R * min(p - 1.0, 1.0)              # moves from R towards 0
            layers.append(alt.Chart(pd.DataFrame({"R": [left], "R2": [R], "f": [f_R]}))
                          .mark_rule(color="red", strokeWidth=2.5)
                          .encode(x=x, x2="R2:Q", y=y))
        if p >= 1.0:
            layers.append(alt.Chart(pd.DataFrame({"R": [R], "f": [f_R]}))
                          .mark_point(size=160, filled=True, color=colour).encode(x=x, y=y))
        if p >= 2.0:
            layers.append(alt.Chart(pd.DataFrame({"R": [0.01], "f": [f_R], "t": [f"f(R) = {f_R:.3f}"]}))
                          .mark_text(align="left", dy=-10, fontSize=14, fontWeight="bold", color="red")
                          .encode(x=x, y=y, text="t:N"))

    # R label on the x-axis
    layers.append(alt.Chart(pd.DataFrame({"R": [R], "f": [0.0], "t": [f"R = {R:.3f}"]}))
                  .mark_text(dy=-8, dx=6, align="left", fontSize=13, color="red")
                  .encode(x=x, y=y, text="t:N"))

    return alt.layer(*layers).properties(height=height)

# --- Density comparison (vehicles / daily users per 1,000 inhabitants) ---
DENSITY_COLOURS = {
    "this city (estimate)": "#E8453C",
    "observed":             "#4C6A92",
    "synthetic (demo)":     "#9B8CFF",
    "reference (entered)":  "#2A9D8F",
}
DENSITY_LABELS = {"per_1000": "Vehicles per 1,000 inhabitants",
                  "users_per_1000": "Daily users per 1,000 inhabitants"}


def density_chart(rows, metric="per_1000", median=None, height=None):
    """Horizontal bars: one bar per city, the estimated city highlighted.

    median: optional value drawn as a dashed line (median of the observed cities).
    """
    df = pd.DataFrame([r for r in rows if r.get(metric) is not None])
    df = df.sort_values(metric, ascending=False)
    df["label"] = df[metric].map(lambda v: f"{v:.2f}")
    types = [t for t in DENSITY_COLOURS if t in set(df["type"])]
    scale = alt.Scale(domain=types, range=[DENSITY_COLOURS[t] for t in types])
    colour = alt.Color("type:N", title=None, scale=scale, legend=alt.Legend(orient="bottom"))
    y = alt.Y("city:N", sort=list(df["city"]), title=None, scale=alt.Scale(paddingInner=0.35),
              axis=alt.Axis(labelLimit=220, labelFontSize=13, ticks=False, domain=False))
    x = alt.X(f"{metric}:Q", title=DENSITY_LABELS[metric], scale=alt.Scale(nice=True, zero=True))
    tooltip = [alt.Tooltip("city:N"), alt.Tooltip("type:N", title="type"),
               alt.Tooltip(f"{metric}:Q", title=DENSITY_LABELS[metric], format=".2f"),
               alt.Tooltip("vehicles:Q", title="vehicles", format=".1f"),
               alt.Tooltip("population:Q", title="population", format=",")]
    base = alt.Chart(df)
    bars = base.mark_bar(cornerRadiusEnd=5).encode(x=x, y=y, color=colour, tooltip=tooltip)
    text = base.mark_text(align="left", dx=6, fontSize=13, fontWeight="bold").encode(
        x=x, y=y, text="label:N", color=alt.Color("type:N", scale=scale, legend=None))
    layers = [bars, text]
    if median is not None:
        rule = alt.Chart(pd.DataFrame({"m": [median]})).mark_rule(strokeDash=[6, 4], color="#6B7080", size=1.5)\
            .encode(x="m:Q")
        layers.append(rule)
    # a fixed pixel height collapses the bars when the legend sits below the chart; use a height per row
    return alt.layer(*layers).properties(height=alt.Step(height or 40))
