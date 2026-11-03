"""IMC fleet-size model - user interface (Streamlit).

Run with:  streamlit run app.py
All calculations live in the imc package; this file only collects inputs and shows results.
"""

import json
import os
import tempfile
import time

import altair as alt
import pandas as pd
import streamlit as st

import imc
from imc.correction import CASCADE_ORDER
from imc.database import load_cities, calibration_cities, add_city, delete_city
from imc.surveys import (load_surveys, suggest_surveys, manual_weights, size_class, add_survey,
                         SAATY, saaty_label, matrix_from_pairs)
from imc.ahp import ahp
from imc.pipeline import predict, make_record
from imc.calibration import suggested_u
from imc.seed import seed
from imc.visual import build_frames, draw_frame, LEGEND, density_chart
from imc.demo import synthetic_cities
from imc.compare import density_table, summary, per_1000
from imc.notation import label as sym_label, latex as sym_latex, name as sym_name, FORMULA_LATEX
from imc.runs import (make_run, save_run, load_runs, delete_run, to_json, from_json, file_stem, run_title,
                      compare_table, changed_inputs, city_as_run)
from imc.report import build_pdf, LOGO

# Put the GitHub address here after publishing (shown in the sidebar and the footer)
REPO_URL = ""

# The database files. The environment variables are only used by the check script,
# so its tests never touch your real database.
CITIES_DB = os.environ.get("IMC_CITIES_DB", "data/cities.json")
SURVEYS_DB = os.environ.get("IMC_SURVEYS_DB", "data/surveys.json")
RUNS_DB = os.environ.get("IMC_RUNS_DB", "data/runs.json")

st.set_page_config(page_title="IMC fleet-size model", page_icon=":material/directions_car:",
                   layout="wide", initial_sidebar_state="expanded")

# Small visual details that the theme (.streamlit/config.toml) cannot set
st.markdown("""
<style>
  .block-container {padding-top: 2.2rem; max-width: 1280px;}
  [data-testid="stMetricValue"] {font-weight: 700; font-size: 1.75rem;}
  [data-testid="stMetricLabel"] p {font-size: 0.85rem; color: #6B7080;}
  .imc-hero {padding: 1.1rem 1.4rem; border-radius: 14px; margin-bottom: .6rem;
             background: linear-gradient(120deg, #FFF3F2 0%, #F4F6FA 60%);
             border: 1px solid #ECEEF3;}
  .imc-hero h1 {margin: 0; padding: 0; font-size: 2.1rem; font-weight: 800; color: #1F2330;}
  .imc-hero p {margin: .25rem 0 0 0; color: #5B6170; font-size: 1.02rem;}
  .imc-foot {color: #8A8F9C; font-size: .82rem; text-align: center; padding: 1.5rem 0 .5rem;}
</style>
""", unsafe_allow_html=True)


def public_demo():
    """True on the hosted web version (set PUBLIC_DEMO = true in the app's Secrets on Streamlit Cloud)."""
    try:
        return bool(st.secrets.get("PUBLIC_DEMO", False))
    except Exception:          # no secrets file on your own computer -> normal mode
        return False


if public_demo():
    # On the web, every visitor gets a private copy of the database for this browser session:
    # cities saved by one visitor are never seen by others and disappear when the page is closed.
    if "db_dir" not in st.session_state:
        st.session_state["db_dir"] = tempfile.mkdtemp(prefix="imc_")
    CITIES_DB = os.path.join(st.session_state["db_dir"], "cities.json")
    SURVEYS_DB = os.path.join(st.session_state["db_dir"], "surveys.json")
    RUNS_DB = os.path.join(st.session_state["db_dir"], "runs.json")

seed(CITIES_DB, SURVEYS_DB)                      # first run: store Konstanz + the survey
cities = load_cities(CITIES_DB)
surveys = load_surveys(SURVEYS_DB)


def section(number, title, icon):
    """Numbered section heading with an icon and a thin divider."""
    st.subheader(f":material/{icon}: {number} · {title}", divider="gray")


# =====================================================================
# SIDEBAR
# =====================================================================
st.logo(str(LOGO), size="large")
with st.sidebar:
    st.markdown(f":gray[Self-calibrating fleet sizing · v{imc.__version__}]")
    if public_demo():
        st.info("Online demo: cities you save are visible only to you and are deleted "
                "when you close the page.", icon=":material/public:")

    st.markdown("**Demo mode**")
    demo = st.toggle("Use 6 synthetic calibration cities",
                     help="Made-up cities whose fleets follow a power curve. Shows how the cascade "
                          "compares and switches forms. Never stored, never real data.")

    st.markdown("**Database**")
    real_cities = load_cities(CITIES_DB)
    n_cal_db = len(calibration_cities(real_cities))
    st.caption(f"{len(real_cities)} {'city' if len(real_cities) == 1 else 'cities'} stored, "
               f"{n_cal_db} with a known fleet.")
    st.dataframe(pd.DataFrame([{"city": c["name"], "R": c["R"],
                                "fleet": c.get("N_obs"),
                                "per 1,000": per_1000(c.get("N_obs"), c.get("P"))} for c in real_cities]),
                 hide_index=True, width="stretch",
                 column_config={"R": st.column_config.NumberColumn(format="%.3f"),
                                "fleet": st.column_config.NumberColumn(format="%.0f"),
                                "per 1,000": st.column_config.NumberColumn(
                                    format="%.2f", help="Vehicles per 1,000 inhabitants")})
    with st.expander("Delete a city", icon=":material/delete:"):
        to_delete = st.selectbox("City", [c["name"] for c in real_cities], key="del_city")
        sure = st.checkbox("Yes, delete it permanently", key="del_sure")
        if st.button("Delete", disabled=not sure):
            delete_city(to_delete, CITIES_DB)
            st.session_state.pop("result", None)
            st.session_state["flash"] = f"{to_delete} was deleted from the database."
            st.rerun()
    st.download_button("Download database (backup)", json.dumps(real_cities, indent=2, ensure_ascii=False),
                       file_name="cities.json", mime="application/json", icon=":material/download:",
                       width="stretch")
    with st.expander("About", icon=":material/info:"):
        st.caption("Implements the AHP–TOPSIS–IMC model of the thesis *Integrated Decision Support Model "
                   "for Determining the Justification of Car-Sharing* (P. Lukács, Széchenyi István "
                   "University, 2026). MIT licence." + (f" [Source code]({REPO_URL})" if REPO_URL else ""))

if demo:
    cities = synthetic_cities()
cal = calibration_cities(cities)

# =====================================================================
# HEADER
# =====================================================================
st.markdown("""<div class="imc-hero"><h1>Car-sharing fleet-size model</h1>
<p>How many shared cars does a town need? AHP · TOPSIS · IMC, recalibrated from every city
whose real fleet is known, with every assumption shown.</p></div>""", unsafe_allow_html=True)
badges = [f":red-badge[:material/sell: v{imc.__version__}]",
          f":blue-badge[:material/location_city: {len(cal)} calibration {'city' if len(cal) == 1 else 'cities'}]"]
if demo:
    badges.append(":violet-badge[:material/science: demo mode]")
if public_demo():
    badges.append(":gray-badge[:material/public: online demo]")
st.markdown(" ".join(badges))
st.caption("Calibration cities: " + ", ".join(c["name"] for c in cal))
if "flash" in st.session_state:                 # one-time message after saving or deleting
    st.success(st.session_state.pop("flash"), icon=":material/check_circle:")
if demo:
    st.error("DEMO MODE: the calibration cities are synthetic. The fleet number is NOT a real estimate.",
             icon=":material/science:")

# =====================================================================
# 1) CITY
# =====================================================================
with st.container(border=True):
    section(1, "City", "location_city")
    c1, c2, c3 = st.columns([2, 1, 1.4])
    name = c1.text_input("City name", value="Mosonmagyarovar")
    country = c2.text_input("Country code", value="HU", max_chars=2).upper()
    P = c3.number_input(sym_label("P"), min_value=1, value=33743, step=1000, key="val_P")
    st.markdown(f":gray-badge[:material/groups: Size class: {size_class(P)}]")

    def optional_number(col, key, default, help_text, fmt="%.4f", step=0.01):
        """A number box with an 'unknown' tick box. Unknown -> None, filled from the database later."""
        unknown = col.checkbox(f"{sym_latex(key)} unknown", key=f"unk_{key}")
        value = col.number_input(sym_label(key), value=default, format=fmt, step=step,
                                 disabled=unknown, help=help_text, key=f"val_{key}")
        return None if unknown else value

    st.markdown("**Mobility parameters**")
    m1, m2, m3, m4 = st.columns(4)
    r_dmr = optional_number(m1, "r_dmr", 0.60, "Share of people making trips on a day (0-1)")
    a0 = optional_number(m2, "a0", 0.20, "Share with a licence but no private car (0-1)")
    w_cs = optional_number(m3, "w_cs", 0.3947, "Share willing to use car sharing (0-1)")
    u_suggest = suggested_u(cal) or 10.0
    u = optional_number(m4, "u", float(u_suggest), "Users per vehicle per day", fmt="%.1f", step=0.5)
    m4.caption(f"Suggested: {u_suggest:g} (calibration cities' median). Keep it to assume the same "
               f"utilisation; change it to test another one. The fleet scales with $1/u$.")

    with st.expander("Optional: cycling share and operator fleet cap", icon=":material/tune:"):
        o1, o2 = st.columns(2)
        use_s = o1.checkbox("Cycling share known (modal split)")
        s = o1.number_input(sym_label("s") + " (0-1)", 0.0, 1.0, 0.15, 0.01, disabled=not use_s, key="val_s") if use_s else None
        use_cap = o2.checkbox("Operator has a maximum fleet")
        N_max = o2.number_input(sym_label("N_max"), 1, 10_000, 20, disabled=not use_cap, key="val_N_max") if use_cap else None

# =====================================================================
# 2) PUBLIC-TRANSPORT INDICATORS (any number of rows)
# =====================================================================
with st.container(border=True):
    section(2, "Public-transport indicators", "directions_bus")
    st.caption("One row per indicator. Add or delete rows freely. 'group' links the indicator to an "
               "AHP criterion. Cost = lower is better, benefit = higher is better. "
               "Enter benchmarks in the same currency and unit as the measured value.")

    template = pd.DataFrame([      # Mosonmagyarovar, thesis Table 3.3 (HUF)
        {"code": "C1", "name": "Crowding",              "group": "comfort",       "kind": "cost",    "measured": 1.73,  "worst": 5.0,   "ideal": 1.0},
        {"code": "C2", "name": "Cost per minute",       "group": "cost",          "kind": "cost",    "measured": 26.39, "worst": 40.0,  "ideal": 20.0},
        {"code": "C3", "name": "Monthly pass per trip", "group": "cost",          "kind": "cost",    "measured": 71.59, "worst": 120.0, "ideal": 40.0},
        {"code": "C4", "name": "Stop density",          "group": "accessibility", "kind": "benefit", "measured": 1.9,   "worst": 0.8,   "ideal": 2.4},
        {"code": "C5", "name": "Headway",               "group": "accessibility", "kind": "cost",    "measured": 35.0,  "worst": 60.0,  "ideal": 20.0},
    ])
    table = st.data_editor(
        template, num_rows="dynamic", width="stretch", key="indicators",
        column_config={
            "code": st.column_config.TextColumn("code", width="small"),
            "kind": st.column_config.SelectboxColumn("kind", options=["cost", "benefit"], required=True,
                                                     help="cost = lower is better · benefit = higher is better"),
            "measured": st.column_config.NumberColumn("measured", help="Value in the city"),
            "worst": st.column_config.NumberColumn("worst", help="Worst benchmark"),
            "ideal": st.column_config.NumberColumn("ideal", help="Ideal benchmark"),
        },
    )
    table = table.dropna(subset=["measured", "worst", "ideal", "group"])   # ignore half-filled rows
    indicators = table.to_dict("records")
    groups = sorted({i["group"] for i in indicators})
    st.caption(f"{len(indicators)} indicators in {len(groups)} groups: {', '.join(groups)}")

# =====================================================================
# 3) WEIGHTS: stored survey, your own AHP comparisons, or manual weights
# =====================================================================
with st.container(border=True):
    section(3, "Criteria weights", "balance")
    st.caption("Criteria are what matters to people (cost, comfort, ...). Any number is allowed. "
               "A criterion only affects the result if at least one indicator in section 2 has it as its "
               "'group': TOPSIS measures the city through indicators.")

    suggestions = suggest_surveys(country, P, surveys, groups)
    usable = [x for x in suggestions if x["tier"] is not None]
    options = ([f"Survey: {x['survey']['city']}" for x in usable]
               + ["Enter AHP comparisons", "Manual weights"])

    w_left, w_right = st.columns([1.25, 1])
    with w_left:
        choice = st.radio("Weights from", options, index=0)
        for x in suggestions:                                  # show every survey with its reason
            marker = "✔" if x["tier"] is not None else "✖"
            st.caption(f"{marker} {x['survey']['city']} — {x['label']} · {x['reason']}")

    # Criteria list for your own comparisons / manual weights: thesis criteria + any indicator group
    default_criteria = ["cost", "comfort", "reliability", "accessibility"]
    default_criteria += [g for g in groups if g not in default_criteria]

    group_weights = {}
    if choice in ("Enter AHP comparisons", "Manual weights"):
        typed = st.text_input("Criteria (comma-separated, any number)", ", ".join(default_criteria),
                              key="criteria_list")
        criteria = []
        for c in typed.split(","):                         # clean up: lower case, no blanks, no repeats
            c = c.strip().lower()
            if c and c not in criteria:
                criteria.append(c)

    if choice == "Enter AHP comparisons":
        if not 2 <= len(criteria) <= 10:
            st.error("AHP needs 2 to 10 criteria.")
        else:
            st.caption("For each pair: slide towards the criterion that matters more. "
                       "9 = extremely more important, 1 = equal.")
            pairs = {}
            cols = st.columns(2)
            k = 0
            for i in range(len(criteria)):
                for j in range(i + 1, len(criteria)):
                    a, b = criteria[i], criteria[j]
                    pairs[(i, j)] = cols[k % 2].select_slider(
                        f"{a} vs {b}", options=SAATY, value=1, key=f"pair_{a}_{b}",
                        format_func=lambda v, a=a, b=b: saaty_label(v, a, b))
                    k += 1
            matrix = matrix_from_pairs(criteria, pairs)
            res = ahp(matrix)
            group_weights = dict(zip(criteria, (float(w) for w in res["weights"])))
            if len(criteria) < 3:
                st.caption("Consistency can't be checked with fewer than 3 criteria.")
            elif res["CR"] >= 0.10:
                st.warning(f"CR = {res['CR']:.1%}: the judgements contradict each other (should be below 10%). "
                           "Check pairs like A > B, B > C but C > A.", icon=":material/warning:")
            else:
                st.success(f"CR = {res['CR']:.1%}: consistent.", icon=":material/check_circle:")

            with st.expander("Save these comparisons as a survey (they then appear as suggestions)"):
                s1, s2, s3, s4 = st.columns(4)
                sv_city = s1.text_input("Survey city", value=name, key="sv_city")
                sv_country = s2.text_input("Country", value=country, max_chars=2, key="sv_country").upper()
                sv_pop = s3.number_input("Population", min_value=1, value=int(P), key="sv_pop")
                sv_n = s4.number_input("Respondents", min_value=1, value=1, key="sv_n")
                if st.button("Save survey"):
                    add_survey({"city": sv_city, "country": sv_country, "population": int(sv_pop),
                                "criteria": criteria, "respondents": int(sv_n), "matrix": matrix}, SURVEYS_DB)
                    st.session_state["flash"] = f"Survey '{sv_city}' saved."
                    st.rerun()

    elif choice == "Manual weights":
        st.caption("Any positive numbers; they are rescaled to sum to 1. Add rows for more criteria.")
        wtable = st.data_editor(pd.DataFrame({"criterion": criteria, "weight": [1.0] * len(criteria)}),
                                num_rows="dynamic", key="manual_w", width="stretch")
        wtable = wtable.dropna()
        raw = {str(r["criterion"]).strip().lower(): float(r["weight"]) for _, r in wtable.iterrows()
               if str(r["criterion"]).strip()}
        try:
            group_weights = manual_weights(raw)
        except ValueError as error:
            st.error(str(error))

    else:
        picked = usable[options.index(choice)]
        group_weights = picked["weights"]

    unused = [g for g in group_weights if g not in groups]
    with w_right:
        st.write("Weights: " + ", ".join(f"{g} **{w:.3f}**" for g, w in group_weights.items()))
        if group_weights:
            wdf = pd.DataFrame({"criterion": list(group_weights), "weight": list(group_weights.values())})
            wdf["used"] = wdf["criterion"].map(lambda g: "used" if g in groups else "no indicator")
            st.altair_chart(
                alt.Chart(wdf).mark_bar(cornerRadiusEnd=4).encode(
                    x=alt.X("weight:Q", title=None, axis=alt.Axis(format=".0%")),
                    y=alt.Y("criterion:N", sort="-x", title=None),
                    color=alt.Color("used:N", legend=None,
                                    scale=alt.Scale(domain=["used", "no indicator"], range=["#E8453C", "#C9CDD6"])),
                    tooltip=["criterion", alt.Tooltip("weight:Q", format=".3f"), "used"])
                .properties(height=alt.Step(30)).configure_view(strokeWidth=0), width="stretch")
    if unused:
        st.info(f"No indicator has the group {', '.join(unused)}, so {'it is' if len(unused) == 1 else 'they are'} "
                f"dropped and the other weights are rescaled. Add an indicator row with that group "
                f"(e.g. punctuality for reliability) to make it count.", icon=":material/info:")

# =====================================================================
# 4) CALCULATE
# =====================================================================
city = {"name": name, "country": country, "P": int(P), "r_dmr": r_dmr, "a0": a0,
        "w_cs": w_cs, "u": u, "s": s, "N_max": N_max}


@st.cache_data(show_spinner=False, max_entries=20)
def pdf_bytes(run_text):
    """PDF of a run; cached, so it is built once per calculation and label."""
    return build_pdf(json.loads(run_text))


result_ok = False
with st.container(border=True):
    section(4, "Result", "query_stats")
    b1, b2 = st.columns([1, 3], vertical_alignment="bottom")
    with b2.expander("Advanced: correction form"):
        forced = st.selectbox("Correction form", ["automatic"] + CASCADE_ORDER,
                              help="Automatic = the cascade chooses. A forced form still shows its test error.")

    # A "fingerprint" of every input: if it differs from the one at the last Calculate,
    # the result on screen is out of date.
    fingerprint = json.dumps([city, indicators, group_weights, forced, demo], sort_keys=True, default=str)

    if b1.button("Calculate", type="primary", icon=":material/calculate:", width="stretch"):
        with st.status("Calculating…", expanded=False) as status:
            st.write("AHP weights and TOPSIS closeness")
            res = predict(city, indicators, group_weights, cities, forced)
            st.write("Correction-function cascade and calibration")
            st.session_state["result"] = res
            st.session_state["fingerprint"] = fingerprint
            st.session_state["run"] = (make_run(res, f"{name} – {choice}", group_weights, choice, forced, demo,
                                                imc.__version__, cities) if res["ok"] else None)
            status.update(label="Calculated", state="complete")

    result = st.session_state.get("result")
    outdated = st.session_state.get("fingerprint") != fingerprint
    if result is None:
        st.info("Fill in the inputs and press **Calculate**.", icon=":material/arrow_upward:")
    else:
        if outdated:
            st.warning("The inputs have changed since the last calculation. Press **Calculate** to update.",
                       icon=":material/sync_problem:")
        for w in result.get("warnings", []):
            st.warning(w, icon=":material/warning:")
        if not result["ok"]:
            for p in result["problems"]:
                st.error(p)
        else:
            result_ok = True

    if result_ok:
        final, cascade = result["final"], result["cascade"]
        rc = result["city"]                                 # the city as calculated (gaps filled)
        rows = density_table(rc["name"], rc["P"], final["N"], rc.get("u"), cities,
                             st.session_state.get("refs_rows", []))
        dens = summary(rows)

        k1, k2, k3, k4, k5 = st.columns([1.3, 1.25, 1, 1, 1.15])
        k1.metric(f"Fleet size {sym_latex('N')}", f"{final['N']:.0f} vehicles", help=f"Exact: {final['N']:.1f}",
                  border=True)
        k2.metric("Per 1,000 inhabitants", f"{rows[0]['per_1000']:.2f}",
                  delta=(f"{dens['ratio'] - 1:+.0%} vs median" if dens else None), delta_color="off",
                  help="Vehicles per 1,000 inhabitants. Compared with the median of the cities whose real fleet "
                       "is known (see the 'Density comparison' tab).", border=True)
        k3.metric(f"PT closeness {sym_latex('Ci')}", f"{result['Ci']:.3f}", border=True)
        k4.metric(f"Deficiency {sym_latex('R')}", f"{result['R']:.3f}", border=True)
        k5.metric(f"Correction form {sym_latex('fR')}", cascade["form"], border=True)

        for key, how in result["estimated"].items():
            st.info(f"{sym_label(key)} = {result['city'][key]:.4g} was not given: {how}.", icon=":material/auto_fix:")

        tab_save, tab_build, tab_curve, tab_dens, tab_log = st.tabs([
            ":material/picture_as_pdf: Save & report", ":material/functions: How the number was built",
            ":material/show_chart: Correction curve", ":material/bar_chart: Density comparison",
            ":material/list: Cascade log"])

        with tab_save:
            base_run = st.session_state.get("run")
            if base_run is None or outdated:
                st.info("Press **Calculate** first, so the report matches the inputs on screen.",
                        icon=":material/sync_problem:")
            else:
                run_label = st.text_input("Name of this calculation", value=base_run["label"], key="run_label",
                                          help="e.g. 'Baseline', 'u = 10', 'with fleet cap'. Shown in the comparison "
                                               "and on the PDF.")
                run = dict(base_run, label=run_label.strip() or base_run["label"])
                run_text = to_json(run)
                c_a, c_b, c_c = st.columns(3)
                if c_a.button("Save calculation", icon=":material/bookmark_add:", width="stretch",
                              help="Stores this calculation so it can be compared with others (section 5)."):
                    save_run(run, RUNS_DB)
                    st.toast(f"Saved: {run['label']}", icon=":material/bookmark_added:")
                try:
                    c_b.download_button("Download PDF report", pdf_bytes(run_text), file_name=f"{file_stem(run)}.pdf",
                                        mime="application/pdf", icon=":material/picture_as_pdf:", width="stretch",
                                        type="primary")
                except Exception as error:          # never let the report break the app
                    c_b.error(f"The PDF could not be built: {error}")
                c_c.download_button("Download data (JSON)", run_text, file_name=f"{file_stem(run)}.json",
                                    mime="application/json", icon=":material/data_object:", width="stretch",
                                    help="Every input and result of this calculation. Can be loaded back in section 5.")
                st.caption("The report contains every input, the indicators, the weights, the correction-function "
                           "selection, the calibration cities used, the density comparison and all warnings. "
                           + ("It is marked as a demonstration, because the calibration cities are synthetic."
                              if demo else ""))

        with tab_build:
            st.latex(FORMULA_LATEX)
            for step_label, value in final["steps"]:
                st.write(f"- {step_label}: **{value:.1f}**")
            for note in final["notes"]:
                st.caption(note)
            if len(cascade["alternatives"]) > 1:
                st.caption("All fittable forms would give: " +
                           ", ".join(f"{k} {v:.1f}" for k, v in cascade["alternatives"].items()))

        with tab_curve:
            # --- Visual walk-through of the cascade ---
            frames = build_frames(cascade, name)
            v1, v2 = st.columns([1, 3])
            play = v1.button("▶ Play the cascade")
            speed = v2.select_slider("Speed", ["slow", "normal", "fast"], value="normal")
            pause = {"slow": 0.6, "normal": 0.3, "fast": 0.12}[speed]

            message_box = st.empty()            # placeholders: redrawn in place, frame after frame
            chart_box = st.empty()

            if play:
                for frame in frames:
                    message_box.markdown(frame["message"])
                    chart_box.altair_chart(draw_frame(frame, cascade, result["cal"]), width="stretch")
                    time.sleep(pause if not frame["message"].startswith("Testing") else pause / 2)
            else:
                step = st.slider("Step", 1, len(frames), len(frames),
                                 help="Drag to look at any single step. The last step is the result.")
                frame = frames[step - 1]
                message_box.markdown(frame["message"])
                chart_box.altair_chart(draw_frame(frame, cascade, result["cal"]), width="stretch")

            lo, hi = cascade["R_range"]
            st.caption(f"{LEGEND}. Black dots: calibration cities. Shaded band: their $R$ range "
                       f"({lo:.3f}–{hi:.3f}); outside it a curve is not backed by data.")

        with tab_dens:
            metric = st.segmented_control("Compare", ["Vehicles per 1,000 inhabitants", "Daily users per 1,000 inhabitants"],
                                          default="Vehicles per 1,000 inhabitants", key="dens_metric")
            col_key = "users_per_1000" if metric == "Daily users per 1,000 inhabitants" else "per_1000"
            med = dens["median_observed"] if (dens and col_key == "per_1000") else None
            shown = [r for r in rows if r.get(col_key) is not None]
            if len(shown) < 2:
                st.info("No other city with a known fleet and population to compare with yet.")
            st.altair_chart(density_chart(rows, col_key, median=med), width="stretch")
            if dens and col_key == "per_1000":
                st.markdown(f"**{rc['name']}**: {dens['estimate']:.2f} vehicles per 1,000 inhabitants, "
                            f"**{dens['ratio']:.2f} ×** the median of {dens['n']} observed "
                            f"{'city' if dens['n'] == 1 else 'cities'} ({dens['median_observed']:.2f}, dashed line).")
            if col_key == "users_per_1000":
                st.caption(r"Daily users per 1,000 inhabitants = vehicles × $u$ per 1,000 inhabitants. For the "
                           r"estimate it is the demand itself ($\bar{\rho}\,T\,f(R)/P$), so it does not change when "
                           r"$u$ is changed; vehicles per 1,000 do.")
            st.caption("A density comparison is a plausibility check, not a validation: cities differ in size, public "
                       "transport and operator strategy, so a different density is not an error by itself."
                       + (" Synthetic demo cities are made up." if demo else ""))
            with st.expander("Add reference values (e.g. published densities of other cities)", icon=":material/add:"):
                st.caption("Type a city and its vehicles per 1,000 inhabitants; write the source next to it. "
                           "Press **Calculate** again to include them in the chart.")
                refs = st.data_editor(pd.DataFrame(st.session_state.get("refs_rows") or
                                                   [{"city": "", "per_1000": None, "source": ""}]),
                                      num_rows="dynamic", key="refs_editor", width="stretch",
                                      column_config={"per_1000": st.column_config.NumberColumn(
                                          "vehicles per 1,000", min_value=0.0, format="%.2f")})
                st.session_state["refs_rows"] = [r for r in refs.to_dict("records") if str(r.get("city") or "").strip()]
            st.dataframe(pd.DataFrame(rows).rename(columns={"per_1000": "vehicles per 1,000",
                                                            "users_per_1000": "daily users per 1,000"}),
                         hide_index=True, width="stretch",
                         column_config={"vehicles": st.column_config.NumberColumn(format="%.1f"),
                                        "population": st.column_config.NumberColumn(format="localized"),
                                        "vehicles per 1,000": st.column_config.NumberColumn(format="%.2f"),
                                        "daily users per 1,000": st.column_config.NumberColumn(format="%.2f")})

        with tab_log:
            for line_text in cascade["log"]:
                st.text(line_text)

# =====================================================================
# 5) COMPARE CALCULATIONS (saved runs, the current one, stored cities, uploaded files)
# =====================================================================
with st.container(border=True):
    section(5, "Compare calculations", "compare_arrows")
    st.caption("Put calculations side by side: the same city with different data (e.g. another $u$, other weights, "
               "a fleet cap), or different cities. Rows that differ are highlighted.")

    saved_runs = load_runs(RUNS_DB)
    pool = {}                                               # title -> run
    current = st.session_state.get("run")
    if current is not None and result_ok and not outdated and current["id"] not in {r["id"] for r in saved_runs}:
        cur = dict(current, label=(st.session_state.get("run_label") or current["label"]) + " (current, not saved)")
        pool[run_title(cur)] = cur
    for r in reversed(saved_runs):
        pool[run_title(r)] = r
    for r in st.session_state.get("uploaded_runs", []):
        pool[run_title(r) + " · file"] = r
    for c in real_cities:
        pool[f"{c['name']} (database)"] = city_as_run(c)

    with st.expander("Load a downloaded calculation (JSON)", icon=":material/upload_file:"):
        files = st.file_uploader("IMC calculation files", type="json", accept_multiple_files=True, key="run_files")
        loaded = []
        for f in files or []:
            try:
                loaded.append(from_json(f.getvalue().decode("utf-8")))
            except ValueError as error:
                st.error(f"{f.name}: {error}")
        if loaded:
            st.session_state["uploaded_runs"] = loaded
            for r in loaded:
                pool[run_title(r) + " · file"] = r

    options = list(pool)
    recent = [t for t in options if t in {run_title(r) for r in saved_runs}][:2]          # newest two saved
    default = list(reversed(recent)) + [t for t in options if "(current" in t][:1]       # oldest first = baseline
    picked = st.multiselect("Calculations to compare", options, default=default,   # no key: default follows new runs

                            placeholder="Choose saved calculations or stored cities")
    chosen = [pool[t] for t in picked]
    if len(chosen) < 2:
        st.info("Choose at least two. Save a calculation in the **Save & report** tab, change an input, "
                "press **Calculate** again and compare.", icon=":material/compare_arrows:")
    if chosen:
        table_rows, differs, columns = compare_table(chosen)
        df = pd.DataFrame(table_rows)

        def mark(row):
            return ["background-color: #FFF1F1" if differs[row.name] else "" for _ in row]

        st.dataframe(df.style.apply(mark, axis=1), hide_index=True, width="stretch",
                     height=min(36 * (len(df) + 1) + 4, 660),
                     column_config={"section": st.column_config.TextColumn(width="small"),
                                    "quantity": st.column_config.TextColumn(width="medium")})
        same_city = [r for r in chosen if r["city"]["name"] == chosen[0]["city"]["name"]]
        if len(same_city) >= 2:
            st.markdown(f"**Same city, different data – {chosen[0]['city']['name']}**")
            base = same_city[0]
            for other in same_city[1:]:
                changes = changed_inputs(base, other)
                nb, no = base["result"].get("N"), other["result"].get("N")
                diff = (f" → fleet {nb:.1f} → {no:.1f} ({(no - nb) / nb:+.0%})" if nb and no else "")
                st.caption(f"*{other['label']}* vs *{base['label']}*: " + ("; ".join(changes) or "no input change") + diff)
        plot = pd.DataFrame([{"calculation": r["label"][:40], "vehicles": r["result"].get("N"),
                              "per 1,000": (r.get("density") or [{}])[0].get("per_1000")} for r in chosen])
        plot = plot.dropna(subset=["vehicles"])
        if len(plot) >= 2:
            st.altair_chart(
                alt.Chart(plot).mark_bar(cornerRadiusEnd=5).encode(
                    x=alt.X("vehicles:Q", title="Fleet size (vehicles)"),
                    y=alt.Y("calculation:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
                    color=alt.value("#E8453C"),
                    tooltip=["calculation", alt.Tooltip("vehicles:Q", format=".1f"),
                             alt.Tooltip("per 1,000:Q", format=".2f")])
                .properties(height=alt.Step(34)), width="stretch")

    if saved_runs:
        with st.expander(f"Saved calculations ({len(saved_runs)})", icon=":material/bookmarks:"):
            st.dataframe(pd.DataFrame([{"name": r["label"], "city": r["city"]["name"], "saved": r["saved_at"],
                                        "fleet": r["result"]["N"], "form": r["result"]["form"],
                                        "demo": r.get("demo", False)} for r in reversed(saved_runs)]),
                         hide_index=True, width="stretch",
                         column_config={"fleet": st.column_config.NumberColumn(format="%.1f")})
            d1, d2 = st.columns([3, 1], vertical_alignment="bottom")
            to_del = d1.selectbox("Delete a saved calculation", [run_title(r) for r in reversed(saved_runs)],
                                  key="run_del")
            if d2.button("Delete", key="run_del_btn", icon=":material/delete:"):
                victim = next(r for r in saved_runs if run_title(r) == to_del)
                delete_run(victim["id"], RUNS_DB)
                st.rerun()
            st.download_button("Download all saved calculations (JSON)",
                               json.dumps(saved_runs, indent=2, ensure_ascii=False), file_name="imc_runs.json",
                               mime="application/json", icon=":material/download:")

# =====================================================================
# 6) SAVE THE CITY TO THE DATABASE (it becomes a calibration city if its fleet is known)
# =====================================================================
with st.container(border=True):
    section(6, "Save city to database", "save")
    if not result_ok:
        st.info("Calculate a result first.", icon=":material/arrow_upward:")
    elif demo:
        st.info("Saving is switched off in demo mode: synthetic cities never enter the database.",
                icon=":material/science:")
    elif outdated:
        st.info("Press **Calculate** first, so the saved values match the inputs on screen.",
                icon=":material/sync_problem:")
    else:
        known = st.checkbox("The real fleet of this city is known (save it as a calibration city)", key="known")
        N_obs = None
        if known:
            N_obs = st.number_input(sym_label("N_obs") + " (vehicles)", min_value=1, value=20, step=1, key="N_obs")
            error = abs(final["N"] - N_obs) / N_obs
            st.write(f"The model predicted **{final['N']:.1f}** before seeing the real fleet of **{N_obs}**: "
                     f"error **{error:.0%}**. This out-of-sample test is stored with the city.")
            st.caption("After saving, the model learns from this city: every later prediction changes.")
            if result["estimated"]:
                st.warning("Some inputs of this city were estimated, not measured: "
                           f"{', '.join(result['estimated'])}. The model would learn partly from guesses. "
                           "Enter the real values first if you have them.", icon=":material/warning:")
        source = st.text_input("Source of the data", placeholder="e.g. operator data 2026, municipal statistics",
                               key="source")

        existing = [c["name"] for c in load_cities(CITIES_DB)]
        if name in existing:
            st.warning(f"'{name}' is already in the database. Saving will replace it.", icon=":material/warning:")

        label = "Save as calibration city" if known else "Save city (no observed fleet)"
        if st.button(label, icon=":material/save:"):
            add_city(make_record(result, N_obs, source), CITIES_DB)
            st.session_state.pop("result", None)
            st.session_state["flash"] = (f"{name} saved" +
                                         (" as a calibration city. The model now learns from it." if known else "."))
            st.rerun()

st.markdown(f"<div class='imc-foot'>IMC fleet-size model v{imc.__version__} · AHP–TOPSIS–IMC · "
            f"P. Lukács, Széchenyi István University, 2026 · MIT licence<br>"
            f"<b>Don’t risk it. <span style='color:#E8453C'>Calculate it.</span></b></div>", unsafe_allow_html=True)
