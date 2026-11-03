"""Demand and fleet size (thesis IMC equations)."""


def interested_people(P, r_dmr, a0, w_cs):
    """Target group T = P * r_dmr * a0 * w_cs  (people per day who would use car sharing).

    P     population
    r_dmr daily mobility rate (share of people making trips on a day)
    a0    share with a driving licence but no access to a private car
    w_cs  willingness to use car sharing (questionnaire)
    """
    return P * r_dmr * a0 * w_cs


def fleet_size(T, f, u):
    """Fleet N = T * f(R) / u.

    T * f = daily users after the public-transport correction.
    u     = users per vehicle per day, so dividing by u gives the number of cars.
    """
    daily_users = T * f
    return daily_users / u