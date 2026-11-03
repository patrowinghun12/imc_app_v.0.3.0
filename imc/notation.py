"""One place for every symbol, so the app, the PDF and the thesis write them the same way.

latex   : for Streamlit labels and text (Streamlit renders $...$)
html    : for the PDF (ReportLab paragraph markup)
plain   : for plain-text places (cascade log, file names)
"""

SYMBOLS = {
    #  key       name                                        latex                    html                                  plain
    "P":      ("Population",                                 r"$P$",                  "<i>P</i>",                            "P"),
    "r_dmr":  ("Daily mobility rate",                        r"$r_{dmr}$",            "<i>r</i><sub><i>dmr</i></sub>",       "r_dmr"),
    "a0":     ("Licence, no car",                            r"$a_0$",                "<i>a</i><sub>0</sub>",                "a0"),
    "w_cs":   ("Willingness to use car sharing",             r"$w_{cs}$",             "<i>w</i><sub><i>cs</i></sub>",        "w_cs"),
    "u":      ("Users per vehicle per day",                  r"$u$",                  "<i>u</i>",                            "u"),
    "s":      ("Cycling share",                              r"$s$",                  "<i>s</i>",                            "s"),
    "N_max":  ("Maximum fleet of the operator",              r"$N_{max}$",            "<i>N</i><sub><i>max</i></sub>",       "N_max"),
    "N":      ("Fleet size",                                 r"$N$",                  "<i>N</i>",                            "N"),
    "N_obs":  ("Observed fleet",                             r"$N_{obs}$",            "<i>N</i><sub><i>obs</i></sub>",       "N_obs"),
    "Ci":     ("Closeness to the ideal (TOPSIS)",            r"$C_i$",                "<i>C</i><sub><i>i</i></sub>",         "Ci"),
    "R":      ("Public-transport deficiency",                r"$R$",                  "<i>R</i>",                            "R"),
    "fR":     ("Correction function",                        r"$f(R)$",               "<i>f</i>(<i>R</i>)",                  "f(R)"),
    "rho":    ("Calibration factor (pooled)",                r"$\bar{\rho}$",         "<i>ρ</i>",                            "rho"),
    # PDF: plain ρ - ReportLab cannot place the combining macron of ρ̄ correctly
    "T":      ("Potential users",                            r"$T$",                  "<i>T</i>",                            "T"),
}


def name(key):
    return SYMBOLS[key][0]


def latex(key):
    return SYMBOLS[key][1]


def html(key):
    return SYMBOLS[key][2]


def plain(key):
    return SYMBOLS[key][3]


def label(key):
    """Streamlit label: 'Daily mobility rate $r_{dmr}$'."""
    return f"{name(key)} {latex(key)}"


FORMULA_LATEX = r"N = \frac{\bar{\rho}\, T\, f(R)}{u}, \qquad T = P \cdot r_{dmr} \cdot a_0 \cdot w_{cs}"
FORMULA_HTML = ("<i>N</i> = <i>ρ</i> · <i>T</i> · <i>f</i>(<i>R</i>) / <i>u</i>,&nbsp;&nbsp; "
                "<i>T</i> = <i>P</i> · <i>r</i><sub><i>dmr</i></sub> · <i>a</i><sub>0</sub> · <i>w</i><sub><i>cs</i></sub>")
