# Changelog

## 0.3.0 – 3 November 2026
### Added
- **Saved calculations.** *Save & report* tab: every calculation can be saved with a name. A saved
  calculation is a frozen copy of all inputs, the indicators, the weights and their source, every
  intermediate result (Ci, R, cascade table, chosen form, ρ̄), the calibration cities known at that
  moment, the density comparison and all warnings. Stored in `data/runs.json` (online: per visitor,
  temporary); downloadable and re-loadable as JSON. Module `imc/runs.py`.
- **Compare calculations** (section 5): any mix of saved calculations, the current one, stored database
  cities and uploaded files side by side; rows that differ are highlighted; for the same city the
  changed inputs and the resulting change of the fleet are listed ("u: 8.4 → 10.0 → fleet 18.2 → 15.3").
- **PDF report** of a calculation (module `imc/report.py`, ReportLab): IMC logo, author, university and
  research title, key results, inputs with proper symbols, indicators, weights, how the number was
  built, the correction-function chart and selection table, calibration cities, density chart,
  warnings, citation; slogan *Don’t risk it. Calculate it.* in the footer of every page. Set in Times
  New Roman where it is installed, otherwise in the bundled, metrically identical Liberation Serif.
- `imc/notation.py`: one table of symbols for the app and the PDF.
- Logo `imc/assets/imc_logo.png` (also in the app's sidebar).
- Checks: section 11 of `check_all.py` (run frozen, JSON round trip, comparison, PDF content and font)
  and an app check that saves a calculation – 47 checks in total.

### Changed
- Notation as in the thesis: $r_{dmr}$, $a_0$, $w_{cs}$, $u$, $s$, $N_{max}$, $C_i$, $R$, $f(R)$, $\bar{\rho}$
  in labels, metrics and captions; the model formula is shown in *How the number was built*.
- Calculate shows its steps in a status box. Database saving is now section 6.
- `requirements.txt`: reportlab added.

## 0.2.0 – 3 November 2026
### Added
- **Density comparison**: vehicles and daily users per 1,000 inhabitants for the estimated city,
  shown next to every city with a known fleet (new tab *Density comparison*, new metric
  *Per 1,000 inhabitants* with the difference from the observed median). Optional reference values
  (e.g. published densities of other cities) can be typed in. Module `imc/compare.py`, checks in
  `check_compare.py` and section 10 of `check_all.py`.
- Weights chart next to the criteria weights (criteria without an indicator shown in grey).
- Theme file `.streamlit/config.toml`.

### Changed
- Interface: numbered sections in bordered cards with icons, header with version and status badges,
  result metrics in cards, result details in tabs (how the number was built, correction curve,
  density comparison, cascade log), optional inputs in an expander, footer with citation.
- Sidebar: database table shows vehicles per 1,000 inhabitants; *About* box.
- `requirements.txt`: Streamlit 1.50 or newer (badges, icons, segmented control).

### Fixed
- Demo mode: no longer shows one "R could not be recomputed" warning per synthetic city
  (synthetic cities are defined by R and are now flagged `synthetic`).
- Sidebar: "1 city stored" instead of "1 cities stored".

## 0.1.0 – October 2026
- First version: AHP–TOPSIS–IMC model, self-calibration from stored cities, correction-function
  cascade with leave-one-out selection, demo mode, database, public-demo mode.
