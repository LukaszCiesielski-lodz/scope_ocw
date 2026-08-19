#!/usr/bin/env python3
"""
Figure 1 for the SCOPE preprint.

Panel (a): Kaplan-Meier survival curves of tau_border, 3 topologies x 2 grids.
Panel (b): median tau_border vs detection threshold, same 6 series.

Reads conf_A_192/runs.json and conf_C_288/runs.json. Computes tau_border with
the SAME definition as scope_analyze.py: first time diss_border reaches `frac`
of its own final value; runs that never reach it are right-censored at horizon.

Pure numpy + matplotlib (no torch). Run locally where the JSON lives:
    python3 make_figure1.py --a conf_A_192/runs.json --c conf_C_288/runs.json
"""
import argparse
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TOPOS = ["distributed", "shell", "central"]
THRESHOLDS = [0.01, 0.05, 0.10, 0.25, 0.50]
PRIMARY = 0.10
DISS_FLOOR = 1e-9  # match scope_analyze

# grayscale-safe palette: dark->light by topology, line style by grid
COLOR = {"central": "#1a1a1a", "shell": "#7a7a7a", "distributed": "#b8b8b8"}
STYLE = {"A": "-", "C": "--"}
LABEL_GRID = {"A": "192³", "C": "288³"}


def tau_border(run, frac):
    """First time diss_border reaches `frac` of its own final value.
    Returns None when never reached (right-censored)."""
    db = np.asarray(run["diss_border"], dtype=float)
    t = np.asarray(run["t"], dtype=float)
    if db.size == 0 or t.size == 0:
        return None
    final = db[-1]
    if not np.isfinite(final) or final <= DISS_FLOOR:
        return None
    hit = np.nonzero(db >= frac * final)[0]
    return float(t[hit[0]]) if len(hit) else None


def arm_taus(runs, topo, frac):
    """Return (event_times, censored_flag) for one topology."""
    taus, censored = [], []
    for r in runs:
        if r.get("topology") != topo:
            continue
        tb = tau_border(r, frac)
        if tb is None:
            # censored at horizon: use last recorded t
            t = np.asarray(r["t"], dtype=float)
            taus.append(float(t[-1]) if t.size else np.nan)
            censored.append(True)
        else:
            taus.append(tb)
            censored.append(False)
    return np.array(taus), np.array(censored, dtype=bool)


def kaplan_meier(taus, censored):
    """Return step points (x, S) of the KM estimator."""
    order = np.argsort(taus)
    taus, censored = taus[order], censored[order]
    n = len(taus)
    x, S = [0.0], [1.0]
    surv = 1.0
    at_risk = n
    i = 0
    while i < n:
        t = taus[i]
        # count events (non-censored) and total at this time
        d = 0
        tied = 0
        j = i
        while j < n and taus[j] == t:
            tied += 1
            if not censored[j]:
                d += 1
            j += 1
        if d > 0:
            surv *= (1.0 - d / at_risk)
            x.append(t); S.append(surv)
        at_risk -= tied
        i = j
    x.append(x[-1]); S.append(S[-1])
    return np.array(x), np.array(S)


def median_tau(taus, censored, frac_note=""):
    """Median of event times (ignoring censored, which sit at horizon)."""
    ev = taus[~censored]
    if ev.size == 0:
        return np.nan
    return float(np.median(ev))


def load(path):
    with open(path) as f:
        d = json.load(f)
    return d["runs"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="conf_A_192/runs.json")
    ap.add_argument("--c", default="conf_C_288/runs.json")
    ap.add_argument("--out", default="figure1")
    args = ap.parse_args()

    runs_A = load(args.a)
    runs_C = load(args.c)
    arms = {"A": runs_A, "C": runs_C}

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(7.1, 3.0))

    # ---- Panel (a): Kaplan-Meier at the primary threshold ----
    for grid, runs in arms.items():
        for topo in TOPOS:
            taus, cens = arm_taus(runs, topo, PRIMARY)
            if taus.size == 0:
                continue
            x, S = kaplan_meier(taus, cens)
            axa.step(x, S, where="post",
                     color=COLOR[topo], linestyle=STYLE[grid], linewidth=1.4,
                     label=f"{topo} {LABEL_GRID[grid]}")
    axa.set_xlabel(r"$\tau_{\mathrm{border}}$ (recorded time units)")
    axa.set_ylabel(r"survival $S(\tau)$")
    axa.set_ylim(-0.02, 1.02)
    axa.set_title("(a)  first-passage survival", fontsize=9, loc="left")
    axa.legend(fontsize=6.5, frameon=False, ncol=2, loc="upper right")
    axa.grid(alpha=0.15)

    # ---- Panel (b): median tau_border vs threshold ----
    for grid, runs in arms.items():
        for topo in TOPOS:
            meds = []
            for fr in THRESHOLDS:
                taus, cens = arm_taus(runs, topo, fr)
                meds.append(median_tau(taus, cens))
            axb.plot([100 * f for f in THRESHOLDS], meds,
                     color=COLOR[topo], linestyle=STYLE[grid], linewidth=1.4,
                     marker="o", markersize=3.5,
                     label=f"{topo} {LABEL_GRID[grid]}")
    axb.set_xlabel("detection threshold (%)")
    axb.set_ylabel(r"median $\tau_{\mathrm{border}}$")
    axb.set_title("(b)  threshold stability", fontsize=9, loc="left")
    axb.set_xticks([1, 5, 10, 25, 50])
    axb.grid(alpha=0.15)

    fig.tight_layout()
    fig.savefig(f"{args.out}.pdf", bbox_inches="tight")
    fig.savefig(f"{args.out}.png", dpi=200, bbox_inches="tight")
    print(f"wrote {args.out}.pdf and {args.out}.png")

    # sanity print: medians at primary threshold
    print("\nmedian tau_border @ 10% (sanity vs scope_analyze):")
    for grid, runs in arms.items():
        row = []
        for topo in TOPOS:
            taus, cens = arm_taus(runs, topo, PRIMARY)
            row.append(f"{topo}={median_tau(taus, cens):.0f}")
        print(f"  {LABEL_GRID[grid]}: " + "  ".join(row))


if __name__ == "__main__":
    main()
