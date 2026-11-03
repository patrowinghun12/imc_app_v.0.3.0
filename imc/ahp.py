"""AHP: priority weights and consistency check (thesis Eqs. 1-3)."""

import numpy as np

# Random index RI (Saaty). Key = number of criteria, value = RI.
# For 4 criteria RI = 0.90, as in the thesis.
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12,
                6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def ahp(matrix):
    """Calculate AHP weights and consistency from a pairwise matrix.

    matrix: square list of lists, e.g. 4x4 for Cost/Comfort/Reliability/Accessibility.
    Returns a dictionary with weights, lambda_max, CI, CR and consistent (True/False).
    """
    # Turn the list of lists into a numpy array, so we can do matrix maths.
    A = np.array(matrix, dtype=float)
    n = A.shape[0]                      # number of criteria (rows)

    # Works for any n from 1 to 10. Saaty's random-index table stops at 10,
    # and AHP judgements become unreliable with more criteria anyway.
    if A.shape != (n, n):
        raise ValueError(f"The matrix must be square, got {A.shape[0]} rows and {A.shape[1]} columns.")
    if n not in RANDOM_INDEX:
        raise ValueError(f"AHP supports 1 to 10 criteria, got {n}.")

    # Eq. (1): divide every element by the sum of its COLUMN.
    # A.sum(axis=0) = the column sums; numpy divides each column by its own sum.
    B = A / A.sum(axis=0)

    # Eq. (2): the weight of each criterion = the mean of its ROW in B.
    weights = B.mean(axis=1)

    # Eq. (3): lambda_max = average of (A @ w)_i / w_i.
    # "A @ weights" is matrix-times-vector multiplication.
    lambda_max = np.mean((A @ weights) / weights)

    CI = (lambda_max - n) / (n - 1)     # consistency index
    RI = RANDOM_INDEX[n]                # random index for n criteria
    CR = CI / RI if RI > 0 else 0.0     # consistency ratio (RI = 0 for n <= 2)

    return {
        "weights": weights,
        "lambda_max": lambda_max,
        "CI": CI,
        "CR": CR,
        "consistent": CR < 0.10,        # thesis rule: CR below 10% is acceptable
    }