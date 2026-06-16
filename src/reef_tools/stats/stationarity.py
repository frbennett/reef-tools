"""
Stationarity and trend tests for hydrological time series.

All tests operate on 1-D arrays (e.g., annual flow totals) and return
dictionaries with p-values, test statistics, and significance flags.

Tests
-----
Pettitt (rank-based CUSUM)  —  step change detection
Mann-Kendall                —  monotonic trend with Theil-Sen slope
Rank-sum (Mann-Whitney)     —  pre/post median comparison
Median crossing (Fisz)      —  randomness / serial independence
Rank-difference (v Neumann) —  randomness / serial dependence

Examples
--------
>>> import numpy as np
>>> from reef_tools.stats.stationarity import pettitt_test, mann_kendall
>>> x = np.random.default_rng(42).normal(0, 1, 50)
>>> pt = pettitt_test(x)
>>> pt["significant"]
False
>>> mk = mann_kendall(x)
>>> mk["direction"]
'increasing'
"""

import numpy as np
from scipy.stats import mannwhitneyu, norm, rankdata


def pettitt_test(series, alpha=0.05):
    """
    Pettitt rank-based CUSUM test for step change detection.

    Compares each observation against all others via ranks. The change
    point is the index where the cumulative rank difference is maximised.

    Parameters
    ----------
    series : array-like, shape (n,)
        Time series (typically annual totals).
    alpha : float, default 0.05
        Significance level.

    Returns
    -------
    dict
        K           : test statistic (max absolute CUSUM of ranks)
        p_value     : approximate two-sided p-value
        significant : whether a step change is detected at ``alpha``
        change_idx  : index of most likely change point (0-based)

    References
    ----------
    Pettitt, A.N. (1979). A non-parametric approach to the change-point
    problem. Applied Statistics, 28(2), 126-135.
    """
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n < 10:
        return {"significant": False, "reason": "series too short (n < 10)"}

    ranks = rankdata(series)
    cum = np.cumsum(ranks)
    t = np.arange(1, n)
    U = 2.0 * cum[:-1] - t * (n + 1)

    K = np.max(np.abs(U))
    change_idx = int(np.argmax(np.abs(U)))
    p_value = min(2.0 * np.exp(-6.0 * K ** 2 / (n ** 3 + n ** 2)), 1.0)

    return {
        "K": K,
        "p_value": p_value,
        "significant": p_value < alpha,
        "change_idx": change_idx,
    }


def mann_kendall(series, alpha=0.05):
    """
    Mann-Kendall non-parametric trend test with Theil-Sen slope.

    Detects monotonic trends without assuming normality, using
    Kendall's tau rank correlation.

    Parameters
    ----------
    series : array-like, shape (n,)
        Time series.
    alpha : float, default 0.05
        Significance level.

    Returns
    -------
    dict
        S           : Kendall S statistic (sum of signs of all pairwise diffs)
        tau         : Kendall rank correlation (-1 to +1)
        Z           : standardised test statistic
        p_value     : two-sided p-value (normal approx. with continuity correction)
        significant : whether a trend is detected at ``alpha``
        slope       : Theil-Sen slope (median of all pairwise slopes)
        direction   : 'increasing', 'decreasing', or 'none'

    References
    ----------
    Mann, H.B. (1945). Nonparametric tests against trend. Econometrica, 13, 245-259.
    Kendall, M.G. (1975). Rank Correlation Methods. Griffin.
    """
    series = np.asarray(series, dtype=float)
    n = len(series)

    # Kendall S
    S = 0
    for i in range(n - 1):
        S += np.sum(np.sign(series[i + 1:] - series[i]))

    # Tie correction
    _, counts = np.unique(series, return_counts=True)
    ties = sum(c * (c - 1) * (2 * c + 5) for c in counts)

    # Variance
    var_S = (n * (n - 1) * (2 * n + 5) - ties) / 18.0

    # Continuity-corrected Z
    if S > 0:
        Z = (S - 1) / np.sqrt(var_S)
    elif S < 0:
        Z = (S + 1) / np.sqrt(var_S)
    else:
        Z = 0.0

    p_value = min(2.0 * (1.0 - norm.cdf(np.abs(Z))), 1.0)
    tau = S / (n * (n - 1) / 2.0)

    # Theil-Sen slope
    slopes = [(series[j] - series[i]) / (j - i)
              for i in range(n - 1) for j in range(i + 1, n)]
    sen_slope = np.median(slopes) if slopes else 0.0

    direction = "increasing" if S > 0 else "decreasing" if S < 0 else "none"

    return {
        "S": int(S),
        "tau": tau,
        "Z": Z,
        "p_value": p_value,
        "significant": p_value < alpha,
        "slope": sen_slope,
        "direction": direction,
    }


def rank_sum_test(pre, post, alpha=0.05):
    """
    Mann-Whitney rank-sum test comparing medians of two samples.

    Typically used to test whether flow before and after a candidate
    change year comes from the same distribution.

    Parameters
    ----------
    pre : array-like
        Observations before the split.
    post : array-like
        Observations after the split.
    alpha : float, default 0.05
        Significance level.

    Returns
    -------
    dict
        pre_median, post_median  : medians of each group
        pre_mean, post_mean      : means of each group
        delta_median             : difference (post - pre)
        delta_pct                : percentage change (may be NaN if pre ~ 0)
        statistic                : Mann-Whitney U statistic
        p_value                  : two-sided p-value
        significant              : whether medians differ at ``alpha``
    """
    pre = np.asarray(pre, dtype=float)
    post = np.asarray(post, dtype=float)

    if len(pre) < 5 or len(post) < 5:
        return {"significant": False, "reason": "groups too small (n < 5)"}

    stat, p_value = mannwhitneyu(pre, post, alternative="two-sided")
    med_pre, med_post = np.median(pre), np.median(post)

    return {
        "pre_median": med_pre,
        "post_median": med_post,
        "pre_mean": np.mean(pre),
        "post_mean": np.mean(post),
        "delta_median": med_post - med_pre,
        "delta_pct": (med_post / med_pre - 1) * 100 if med_pre > 0 else np.nan,
        "statistic": stat,
        "p_value": p_value,
        "significant": p_value < alpha,
    }


def median_crossing_test(series, alpha=0.05):
    """
    Fisz median crossing test for serial independence.

    Under randomness, the series should cross its own median roughly
    n/2 times.  Fewer crossings -> positive autocorrelation (persistence).
    More crossings   -> negative autocorrelation (oscillation).

    Parameters
    ----------
    series : array-like, shape (n,)
        Time series.
    alpha : float, default 0.05
        Significance level.

    Returns
    -------
    dict
        n_crossings  : observed crossing count
        expected     : expected crossings under H0
        Z            : standardised test statistic
        p_value      : two-sided p-value
        significant  : whether randomness is rejected at ``alpha``
        description  : 'independent', 'persistent (autocorrelated)',
                       or 'oscillating (neg. autocorr)'
    """
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n < 10:
        return {"significant": False, "reason": "series too short"}

    median = np.median(series)
    above = series >= median
    n_crossings = int(sum(1 for i in range(1, n) if above[i] != above[i - 1]))

    mu_c = (n - 1) / 2.0
    sigma_c = np.sqrt((n - 1) / 4.0)
    Z = (n_crossings - mu_c) / sigma_c if sigma_c > 0 else 0.0
    p_value = min(2.0 * (1.0 - norm.cdf(np.abs(Z))), 1.0)

    if n_crossings < mu_c - 1.96 * sigma_c:
        desc = "persistent (autocorrelated)"
    elif n_crossings > mu_c + 1.96 * sigma_c:
        desc = "oscillating (neg. autocorr)"
    else:
        desc = "independent"

    return {
        "n_crossings": n_crossings,
        "expected": mu_c,
        "Z": Z,
        "p_value": p_value,
        "significant": p_value < alpha,
        "description": desc,
    }


def rank_difference_test(series, alpha=0.05):
    """
    von Neumann ratio test on ranks for serial independence.

    If the ranks are randomly ordered, the von Neumann ratio
    (sum of squared successive differences of ranks) is approx 2.
    RVN < 1.5 -> trend or positive autocorrelation.
    RVN > 2.5 -> alternation or negative autocorrelation.

    Parameters
    ----------
    series : array-like, shape (n,)
        Time series.
    alpha : float, default 0.05
        Significance level.

    Returns
    -------
    dict
        RVN          : von Neumann ratio of ranks
        Z            : standardised test statistic
        p_value      : two-sided p-value
        significant  : whether randomness is rejected at ``alpha``
        description  : 'independent', 'trend/autocorrelated', or 'alternating'
    """
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n < 10:
        return {"significant": False, "reason": "series too short"}

    ranks = rankdata(series)
    S = np.sum((ranks[1:] - ranks[:-1]) ** 2)

    E_S = n * (n ** 2 - 1) / 6.0
    var_S = n * (n - 2) * (n ** 2 - 1) / 36.0
    var_ranks = (n ** 2 - 1) / 12.0
    RVN = S / ((n - 1) * var_ranks)

    Z = (S - E_S) / np.sqrt(var_S) if var_S > 0 else 0.0
    p_value = min(2.0 * (1.0 - norm.cdf(np.abs(Z))), 1.0)

    if RVN < 1.5:
        desc = "trend/autocorrelated"
    elif RVN > 2.5:
        desc = "alternating"
    else:
        desc = "independent"

    return {
        "RVN": RVN,
        "Z": Z,
        "p_value": p_value,
        "significant": p_value < alpha,
        "description": desc,
    }
