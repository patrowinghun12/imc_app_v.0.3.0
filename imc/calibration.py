"""Calibration: learn the realisation factor rho from cities with an observed fleet.

    vehicle demand of a city = T * f(R) / u     (cars needed if ALL corrected demand were realised)
    rho_i = N_obs_i / vehicle demand_i          (Konstanz: 0.607, the thesis rho)

rho is BEHAVIOURAL (how much stated willingness turns into real use), so it is the part
that is transferred to other cities. u is OPERATIONAL (users per car per day) and belongs
to each city: change it and the fleet changes.

Prediction for a new city:  N = rho * T * f(R) / u
If the new city's u equals the calibration city's u, this is exactly the thesis result
(the thesis "u cancels" is this special case).
"""

import math
import statistics

from imc.correction import quadratic
from imc.demand import interested_people


def corrected_demand(city, f_func=quadratic):
    """T * f(R): interested people after the public-transport correction."""
    T = interested_people(city["P"], city["r_dmr"], city["a0"], city["w_cs"])
    return T * f_func(city["R"])


def vehicle_demand(city, f_func=quadratic):
    """T * f(R) / u: cars needed if all the corrected demand were realised."""
    return corrected_demand(city, f_func) / city["u"]


def rho_for_city(city, f_func=quadratic):
    """rho of ONE calibration city."""
    return city["N_obs"] / vehicle_demand(city, f_func)


def pooled_rho(cal_cities, f_func=quadratic):
    """Combine the rho of all calibration cities: geometric mean (average on the log scale)."""
    logs = [math.log(rho_for_city(c, f_func)) for c in cal_cities]
    return math.exp(sum(logs) / len(logs))


def predict_fleet(city, rho, f_func=quadratic):
    """Calibrated fleet for any city: N = rho * T * f(R) / u (the city's OWN u)."""
    return rho * vehicle_demand(city, f_func)


def suggested_u(cal_cities):
    """Suggested u for a new city: the median u of the calibration cities."""
    values = [c["u"] for c in cal_cities if c.get("u") is not None]
    return statistics.median(values) if values else None