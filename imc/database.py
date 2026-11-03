"""City database: a JSON text file holding every city the program knows.

A city with an observed fleet ("N_obs") is a CALIBRATION city: the model learns from it.
A city without one can only be predicted.
"""

import json
from pathlib import Path


def _plain(value):
    """Help json save numpy/pandas numbers: float64(0.25) -> 0.25."""
    return value.item() if hasattr(value, "item") else str(value)


def load_cities(path):
    """Read all cities from the JSON file. Returns an empty list if the file doesn't exist yet."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def save_cities(cities, path):
    """Write all cities to the JSON file (creates the folder if needed)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        # indent=2 makes the file readable for humans; ensure_ascii=False keeps á, ö, ü
        # default=_plain: numbers coming from numpy/pandas (e.g. float64) are turned into plain numbers
        json.dump(cities, file, indent=2, ensure_ascii=False, default=_plain)


def add_city(city, path):
    """Add a city, or replace it if a city with the same name is already stored."""
    cities = load_cities(path)
    cities = [c for c in cities if c["name"] != city["name"]]   # drop the old version, if any
    cities.append(city)
    save_cities(cities, path)
    return cities


def calibration_cities(cities):
    """Only the cities with an observed fleet: these are the ones the model can learn from."""
    return [c for c in cities if c.get("N_obs") is not None]


def delete_city(name, path):
    """Remove a city by name. Returns the remaining cities."""
    cities = [c for c in load_cities(path) if c["name"] != name]
    save_cities(cities, path)
    return cities