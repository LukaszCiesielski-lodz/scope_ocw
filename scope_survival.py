#!/usr/bin/env python3
"""
Survival analysis of first-passage times (CRITERIA_v2, ratified 2026-07-23)
==========================================================================
tau_border is a first-passage time under a common horizon T: runs whose
structure never reaches the boundary within T are RIGHT-CENSORED, not
missing. Mann-Whitney on such data is not valid -- it has no rank for a
non-event -- so the ordering test is log-rank (Mantel-Cox) on Kaplan-Meier
curves, which is built for exactly this.

Kaplan-Meier curves are also the honest figure for the paper: a dead or
non-exporting arm appears as a plateau at S=1 rather than vanishing from
the plot, which is how the extinct `shell` arm hid in v1.

Multiplicity: Holm correction across all pairwise comparisons and grid
sizes (3 pairs x 2 sizes = 6).

Mann-Whitney is retained only as a cross-check for the uncensored case,
where the two tests should agree.
"""

import numpy as np
from scipy.stats import CensoredData, chi2 as chi2_dist, logrank, mannwhitneyu


def km_curve(times, observed, horizon):
    """Kaplan-Meier survival curve with Greenwood log-log confidence band.

    `times`    : event time per run; use `horizon` for censored runs
    `observed` : True if the event happened, False if right-censored
    Returns (t_grid, S, lo, hi) where S is the fraction of runs that have
    NOT yet crossed the boundary.
    """
    times = np.asarray(times, dtype=float)
    observed = np.asarray(observed, dtype=bool)
    order = np.argsort(times)
    times, observed = times[order], observed[order]

    t_grid, S_vals, lo_vals, hi_vals = [0.0], [1.0], [1.0], [1.0]
    S, cum_var = 1.0, 0.0
    n_at_risk = len(times)

    for t in np.unique(times[observed]):
        d = int(np.sum((times == t) & observed))
        n = int(np.sum(times >= t))
        if n <= 0:
            continue
        S *= (1.0 - d / n)
        if n > d:
            cum_var += d / (n * (n - d))
        # log-log transform keeps the band inside [0,1]
        if 0.0 < S < 1.0 and cum_var > 0:
            se = np.sqrt(cum_var) / abs(np.log(S))
            z = 1.96
            lo = S ** np.exp(z * se)
            hi = S ** np.exp(-z * se)
        else:
            lo = hi = S
        t_grid.append(float(t))
        S_vals.append(S)
        lo_vals.append(float(lo))
        hi_vals.append(float(hi))
        n_at_risk = n

    if t_grid[-1] < horizon:
        t_grid.append(float(horizon))
        S_vals.append(S_vals[-1])
        lo_vals.append(lo_vals[-1])
        hi_vals.append(hi_vals[-1])
    return (np.array(t_grid), np.array(S_vals),
            np.array(lo_vals), np.array(hi_vals))


def to_censored(taus, horizon):
    """Build a scipy CensoredData from tau values; None -> right-censored."""
    ev = [t for t in taus if t is not None]
    cens = [horizon for t in taus if t is None]
    if cens:
        return CensoredData(uncensored=np.array(ev, dtype=float),
                            right=np.array(cens, dtype=float))
    return CensoredData(uncensored=np.array(ev, dtype=float))


def logrank_pair(taus_a, taus_b, horizon):
    """Two-sample log-rank. Returns dict with chi2, p, and censoring counts."""
    n_cens_a = sum(t is None for t in taus_a)
    n_cens_b = sum(t is None for t in taus_b)
    if len(taus_a) - n_cens_a == 0 and len(taus_b) - n_cens_b == 0:
        return {"chi2": None, "p": None, "n_cens": [n_cens_a, n_cens_b],
                "note": "zadne ramie nie mialo zdarzenia — test niemozliwy"}
    a, b = to_censored(taus_a, horizon), to_censored(taus_b, horizon)
    res = logrank(a, b)
    return {"chi2": float(res.statistic ** 2), "p": float(res.pvalue),
            "n_cens": [n_cens_a, n_cens_b],
            "censored": bool(n_cens_a or n_cens_b)}


def mannwhitney_crosscheck(taus_a, taus_b):
    """Only valid with no censoring; reported as a cross-check, never alone."""
    if any(t is None for t in taus_a) or any(t is None for t in taus_b):
        return {"p": None, "note": "cenzura obecna — MW niewazny"}
    a = np.asarray(taus_a, dtype=float)
    b = np.asarray(taus_b, dtype=float)
    if len(a) < 2 or len(b) < 2:
        return {"p": None, "note": "za malo danych"}
    try:
        u, p = mannwhitneyu(a, b, alternative="two-sided")
    except ValueError as e:
        return {"p": None, "note": str(e)}
    return {"U": float(u), "p": float(p)}


def holm(pvals):
    """Holm-Bonferroni step-down adjusted p-values, order preserved.

    None entries pass through as None and do not consume a comparison.
    """
    idx = [i for i, p in enumerate(pvals) if p is not None]
    if not idx:
        return list(pvals)
    m = len(idx)
    order = sorted(idx, key=lambda i: pvals[i])
    adj = list(pvals)
    running = 0.0
    for rank, i in enumerate(order):
        val = (m - rank) * pvals[i]
        running = max(running, val)          # enforce monotonicity
        adj[i] = float(min(1.0, running))
    return adj


def curves_overlap(km_a, km_b):
    """Do two KM confidence bands overlap over their whole common support?

    CRITERIA_v2 requires this for a NEGATIVE verdict: equivalence must be
    shown actively, not inferred from a failure to reach significance.
    """
    ta, _, loa, hia = km_a
    tb, _, lob, hib = km_b
    grid = np.union1d(ta, tb)
    grid = grid[(grid >= max(ta[0], tb[0])) & (grid <= min(ta[-1], tb[-1]))]
    if len(grid) == 0:
        return False
    def step(t_arr, v_arr, q):
        return v_arr[np.searchsorted(t_arr, q, side="right") - 1]
    la, ha = step(ta, loa, grid), step(ta, hia, grid)
    lb, hb = step(tb, lob, grid), step(tb, hib, grid)
    return bool(np.all((la <= hb) & (lb <= ha)))
