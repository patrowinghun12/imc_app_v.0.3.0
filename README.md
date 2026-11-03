# IMC fleet-size model – self-calibrating application

Decision-support application for estimating the fleet size of a car-sharing service in small and
medium-sized cities. It implements the AHP–TOPSIS–IMC model of the thesis
*Integrated Decision Support Model for Determining the Justification of Car-Sharing*
(Patrik Lukács, Széchenyi István University, 2026), Chapter 5.

The user enters the data of a city (population, mobility parameters, public transport indicators
and criteria weights) and receives a fleet estimate together with every assumption behind it.
Cities whose real fleet is known can be stored as calibration cities; the model recalibrates itself
from them. Konstanz is stored as the first calibration city when the application starts for the first time.

## Try it online

[Link to the hosted demo – add after deployment]

The hosted version is a demonstration: data entered there are processed on the hosting server
and may be visible to other visitors until the server restarts. For real city data, run the
application on your own computer as described below.

## Run it on your own computer

Requirements: Python 3.10 or newer.

```bash
# 1. download the code (or use "Code → Download ZIP" on GitHub and unzip it)
git clone <repository URL>
cd imc_app

# 2. create a virtual environment and install the packages
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. start the application – it opens in the web browser
streamlit run app.py
```

## Save, compare and report a calculation

After **Calculate**, the tab *Save & report* offers:

- **Save calculation** – keeps a frozen copy of the calculation: every input, every intermediate result
  and the calibration cities the model knew at that moment. Because the model learns, the same city
  gives a different number once a new calibration city is stored; a saved calculation keeps what was
  predicted and why.
- **Download PDF report** – a report with the IMC logo, author and university, all inputs, the
  correction-function selection, the calibration cities, the density comparison and all warnings.
- **Download data (JSON)** – the same calculation as a file; it can be loaded back later.

Section *5 Compare calculations* puts saved calculations, the current one, stored cities and loaded
files side by side, e.g. the same city with another vehicle use u, other weights or a fleet cap.

The PDF is set in Times New Roman when it is installed (macOS, Windows). Times New Roman may not be
redistributed, so the repository ships the metrically identical Liberation Serif
(`imc/assets/fonts`, SIL Open Font License), which is used everywhere else, e.g. on Streamlit Cloud.

## Density comparison (vehicles per 1,000 inhabitants)

After **Calculate**, the metric *Per 1,000 inhabitants* and the tab *Density comparison* place the
estimate next to every city with a known fleet:

- **vehicles per 1,000 inhabitants** = 1000 · N / P – what the operator has to provide; it depends on
  the vehicle use u;
- **daily users per 1,000 inhabitants** = 1000 · N · u / P – the demand itself; for an estimate it does
  not change when u is changed.

Reference values of other cities (e.g. from published statistics) can be typed in for comparison.
The comparison is a plausibility check, not a validation: cities differ in size, public transport
and operator strategy.

## Publish it online (GitHub + Streamlit Community Cloud)

1. **GitHub** – in PyCharm: *Git → GitHub → Share Project on GitHub*, repository name e.g.
   `imc-fleet-model`, public. Check that `.streamlit/config.toml` is included and that no
   `data/*.json` file is uploaded (they are listed in `.gitignore`).
2. **Streamlit Cloud** – sign in at share.streamlit.io with the GitHub account → *Create app* →
   *Deploy a public app from GitHub* → repository `imc-fleet-model`, branch `main`, main file `app.py`.
3. *Advanced settings*: Python 3.12; under *Secrets* write `PUBLIC_DEMO = true`. In this mode every
   visitor gets a private, temporary database.
4. *Deploy*. Put the address of the app under *Try it online* above and into `REPO_URL` in `app.py`.
5. Every later push to `main` updates the online app automatically.

## Check that it reproduces the thesis

```bash
python check_all.py
python check_compare.py
```

The script compares the program with the published results of the thesis (AHP weights, closeness
indices, forward and backward runs, the factor ρ, the re-applied fleet for Mosonmagyaróvár) and with
synthetic test cases. Test data are written to separate `data/*_check.json` files; the real database
is never touched.

## Project structure

| Path | Content |
|---|---|
| `app.py` | Streamlit user interface |
| `imc/ahp.py`, `imc/surveys.py` | AHP weights, consistency check, stored surveys and their ranking |
| `imc/topsis.py` | Reference-based TOPSIS, closeness index Cᵢ and deficiency R |
| `imc/demand.py`, `imc/correction.py` | IMC demand model and correction functions |
| `imc/calibration.py`, `imc/fitting.py`, `imc/cascade.py` | Factor ρ, fitting of the correction functions, choice by leave-one-out testing |
| `imc/inputs.py`, `imc/adjustments.py` | Input checks, gap filling, cycling adjustment, fleet cap |
| `imc/pipeline.py` | One run from inputs to fleet estimate |
| `imc/database.py`, `imc/seed.py` | City database (`data/cities.json`) and first-run data |
| `imc/visual.py`, `imc/demo.py` | Animated explanation and synthetic demonstration cities |
| `imc/compare.py` | Vehicles and daily users per 1,000 inhabitants, density comparison |
| `imc/runs.py` | Saved calculations: freeze, store, load, compare |
| `imc/report.py` | PDF report of a calculation |
| `imc/notation.py` | Symbols used in the app and the report |
| `imc/assets/` | Logo and the bundled Liberation Serif font |
| `.streamlit/config.toml` | Colours and font of the interface |
| `CHANGELOG.md` | What changed in each version |
| `check_*.py` | Automated checks; `check_all.py` runs them all |

## Data

On first start the application writes Konstanz (calibration city) and the Mosonmagyaróvár AHP survey
to `data/cities.json` and `data/surveys.json`. The Konstanz values are those reported in the thesis
(operator data and consultation, October 2026). Your own cities are stored only in these local files.

## Citation

If you use the application, please cite the thesis:
Lukács, P. (2026). *Integrated Decision Support Model for Determining the Justification of Car-Sharing*.
Thesis, Széchenyi István University, Győr. Software: [repository URL / DOI].

## Licence

MIT – see `LICENSE`.
