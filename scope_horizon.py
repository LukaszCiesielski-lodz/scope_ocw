#!/usr/bin/env python3
"""
Horizon rule (CRITERIA_v2 §7)
=============================
The horizon must be long enough that a censored run means "this arm does
not export", never "this arm is slower than we watched". Otherwise the
log-rank test cannot tell a dead arm from a slow one, which is the exact
failure the criteria exist to prevent.

Plateau is defined RELATIVE, not as a derivative against an absolute
threshold. An absolute cut on |d(diss_border)/dt| has no scale-free
meaning here: diss_border rises from 0 to ~1.6e-3 over ~5000 units of
pattern time, so its mean normalized rate is ~2e-4 per unit -- any
threshold picked without checking that scale (0.02 per unit was the first
draft, 100x too permissive) marks a still-rising arm as plateaued.

  plateau time t* := earliest t such that for ALL later samples,
                     |y(t) - y(T)| / y(T) < tol      (tol = 0.02)

i.e. the trajectory has entered and stayed inside a 2% band around its
final value. Dimensionless, and it means what it says.

  horizon T_next := 2 x max over arms of t*

An arm that never enters the band has no plateau; the horizon is then
unknown-but-larger and the probe must be rerun longer.
"""

import numpy as np

TOL = 0.02          # relative half-width of the plateau band
LAST_FRAC = 0.20    # plateau must hold over at least the final 20% of the run


def plateau_time(t, y, tol=TOL):
    """Earliest time from which y stays within `tol` of its final value.

    Returns None if the trajectory never settles (still moving at T).
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    y_final = y[-1]
    if not np.isfinite(y_final) or y_final <= 0:
        return None
    dev = np.abs(y - y_final) / y_final
    outside = np.nonzero(dev >= tol)[0]
    if len(outside) == 0:
        return float(t[0])
    if outside[-1] >= len(y) - 1:
        return None                      # still outside the band at T
    return float(t[outside[-1] + 1])


def arm_plateaus(runs, key="diss_border", tol=TOL):
    """Plateau time per topology arm (median over runs in the arm)."""
    out = {}
    for topo in sorted({r["topology"] for r in runs}):
        arm = [r for r in runs if r["topology"] == topo]
        ts = [plateau_time(r["t"], r[key], tol) for r in arm]
        if any(x is None for x in ts):
            out[topo] = None             # at least one run never settled
        else:
            out[topo] = float(np.median(ts))
    return out


def horizon_rule(runs, key="diss_border", tol=TOL, last_frac=LAST_FRAC):
    """Apply CRITERIA_v2 §7. Returns a dict; `horizon` is None if the probe
    was too short, in which case the probe must be rerun, not reinterpreted.
    """
    T = float(np.max([r["t"][-1] for r in runs]))
    plats = arm_plateaus(runs, key=key, tol=tol)
    settled = {k: v for k, v in plats.items() if v is not None}
    unsettled = [k for k, v in plats.items() if v is None]

    # validity: the plateau must hold over at least the final `last_frac`
    holds = {k: (v <= (1.0 - last_frac) * T) for k, v in settled.items()}

    if unsettled or not settled or not all(holds.values()):
        return {"horizon": None, "T_probe": T, "plateau": plats,
                "holds_last_frac": holds, "unsettled": unsettled,
                "verdict": "sonda za krotka — powtorzyc dluzej, nie "
                           "reinterpretowac"}
    slowest = max(settled, key=lambda k: settled[k])
    return {"horizon": 2.0 * settled[slowest], "T_probe": T,
            "plateau": plats, "holds_last_frac": holds, "unsettled": [],
            "slowest_arm": slowest,
            "verdict": "ok"}


def tau_scaling_exponent(tau_by_n):
    """Fit tau ~ n^alpha. CRITERIA_v2 §7 requires steps to be revised upward
    if alpha > 1 -- constant-speed fronts imply alpha = 1, so a steeper
    exponent means transport is not purely frontal and steps proportional to
    n would under-run the larger grids.

    `tau_by_n` : {n: tau}
    """
    ns = np.array(sorted(tau_by_n), dtype=float)
    taus = np.array([tau_by_n[int(n)] for n in ns], dtype=float)
    ok = np.isfinite(taus) & (taus > 0)
    if ok.sum() < 2:
        return None
    alpha, _ = np.polyfit(np.log(ns[ok]), np.log(taus[ok]), 1)
    return float(alpha)
