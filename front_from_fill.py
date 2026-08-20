#!/usr/bin/env python3
"""
Front-expansion proxy from fill(t), normalized, plus transport time.

The referee's naive model: tau = activation + distance/front_speed. Fitting
that to the medians gave front speeds differing by ~1.8x between shell and
central -- i.e. constant-speed transport does NOT close on the data. Something
else (topology-dependent activation? accelerating front? surface/volume of
seed?) is present.

runs.json stores no front position, but it stores fill(t) = fraction of the
domain with v>0.1 at each recorded step. fill(t=0) is NOT zero: seed volume is
matched at ~0.7% of the domain, so raw fill starts already above the naive 5%
milestone in some cases -- an initialization artifact, not activation. We
normalize it out: f_norm(t) = (fill(t) - fill(0)) / (1 - fill(0)), so f_norm
always starts at 0 regardless of seed footprint.

The expansion RATE d(f_norm)/dt and the time to reach f_norm milestones are
model-free proxies for how fast structure spreads. If the three topologies
expand at the SAME rate once activated, the tau ordering is pure geometry
(distance). If they expand at DIFFERENT rates, the effect has a shape/topology
component -- which is the referee's open question, answerable from existing
data.

We also decompose tau_border (first passage of diss_border through 10% of its
final value -- same definition as scope_analyze.tau_border) into:
    t_act           = median time to f_norm = 10%  (activation/maturation proxy)
    tau_border      = median tau_border (as in the frozen tables)
    transport_time  = tau_border - t_act  (pure transport time to the border,
                                            after the seed has matured)

Pure numpy. Run where the JSON lives:
    python3 front_from_fill.py --runs conf_A_192/runs.json
"""
import argparse
import json
import numpy as np

TOPOS = ["distributed", "shell", "central"]
TAU_FRAC = 0.10          # frozen: primary threshold, matches scope_analyze
DISS_FLOOR = 1e-8


def load(path):
    with open(path) as f:
        return json.load(f)["runs"]


def tau_border(run, frac=TAU_FRAC):
    """First time diss_border reaches `frac` of its own final value.

    Copied from scope_analyze.tau_border. Returns None when the boundary is
    never reached -> right-censored.
    """
    db = np.asarray(run["diss_border"], dtype=float)
    t = np.asarray(run["t"], dtype=float)
    final = db[-1]
    if not np.isfinite(final) or final <= DISS_FLOOR:
        return None
    hit = np.nonzero(db >= frac * final)[0]
    return float(t[hit[0]]) if len(hit) else None


def per_topo(runs, topo):
    """Stack fill(t) and t across runs of one topology (they share the grid)."""
    ts, fills = [], []
    for r in runs:
        if r.get("topology") != topo:
            continue
        ts.append(np.asarray(r["t"], dtype=float))
        fills.append(np.asarray(r["fill"], dtype=float))
    return ts, fills


def normalize_fill(fill):
    """f_norm(t) = (fill(t) - fill(0)) / (1 - fill(0))."""
    f0 = fill[0]
    denom = 1.0 - f0
    if denom <= 0:
        return np.full_like(fill, np.nan)
    return (fill - f0) / denom


def time_to_level(t, series, level):
    """First time `series` crosses `level`. None if never."""
    hit = np.nonzero(series >= level)[0]
    return float(t[hit[0]]) if len(hit) else None


def milestone_table(runs, levels, use_norm):
    """Return {topo: {level: median_time}} for raw fill or f_norm."""
    table = {topo: {} for topo in TOPOS}
    for lv in levels:
        for topo in TOPOS:
            ts, fills = per_topo(runs, topo)
            times = []
            for t, f in zip(ts, fills):
                series = normalize_fill(f) if use_norm else f
                tt = time_to_level(t, series, lv)
                if tt is not None:
                    times.append(tt)
            table[topo][lv] = np.median(times) if times else np.nan
    return table


def print_milestone_table(table, levels, title):
    print(f"=== {title} (median over runs) ===")
    print(f"{'level':>6} | " + " | ".join(f"{t:>11}" for t in TOPOS))
    for lv in levels:
        row = []
        for topo in TOPOS:
            med = table[topo][lv]
            row.append(f"{med:>11.0f}" if np.isfinite(med) else f"{'--':>11}")
        print(f"{lv*100:>5.0f}% | " + " | ".join(row))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="conf_A_192/runs.json")
    args = ap.parse_args()
    runs = load(args.runs)

    levels = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50]

    # raw fill, kept for comparison
    raw_table = milestone_table(runs, levels, use_norm=False)
    print_milestone_table(raw_table, levels,
                           "time to reach RAW fill milestones")

    # normalized fill -- the corrected version
    norm_table = milestone_table(runs, levels, use_norm=True)
    print_milestone_table(norm_table, levels,
                           "time to reach NORMALIZED f_norm milestones "
                           "(f_norm = (fill-fill0)/(1-fill0))")

    # expansion rate between 10% and 40% f_norm (the growth phase)
    print("=== mean expansion rate d(f_norm)/dt in the 10%->40% window ===")
    print("(if topologies share a rate, tau ordering is geometry/distance;")
    print(" if rates differ, there is a shape/topology component)")
    rates = {}
    for topo in TOPOS:
        t10 = norm_table[topo].get(0.10)
        t40 = norm_table[topo].get(0.40)
        if t10 and t40 and np.isfinite(t10) and np.isfinite(t40) and t40 > t10:
            rate = (0.40 - 0.10) / (t40 - t10)
            rates[topo] = rate
            print(f"  {topo:>11}: {rate:.3e} /unit   (t10={t10:.0f}, t40={t40:.0f})")
        else:
            rates[topo] = None
            print(f"  {topo:>11}: rate undefined (t10={t10}, t40={t40})")
    print()

    # transport time: tau_border - t_act(f_norm=10%)
    print("=== transport time: tau_border - t_act (f_norm=10% activation proxy) ===")
    print(f"{'topology':>11} | {'t_act':>10} | {'tau_border':>10} | {'transport':>10}")
    for topo in TOPOS:
        t_act = norm_table[topo].get(0.10)
        taus = [tau_border(r) for r in runs if r["topology"] == topo]
        taus = [x for x in taus if x is not None]
        tau_med = np.median(taus) if taus else np.nan
        act_str = f"{t_act:>10.0f}" if t_act is not None and np.isfinite(t_act) else f"{'--':>10}"
        tau_str = f"{tau_med:>10.0f}" if np.isfinite(tau_med) else f"{'--':>10}"
        if t_act is not None and np.isfinite(t_act) and np.isfinite(tau_med):
            transport = tau_med - t_act
            transport_str = f"{transport:>10.0f}"
        else:
            transport_str = f"{'--':>10}"
        print(f"{topo:>11} | {act_str} | {tau_str} | {transport_str}")
    print()

    # referee's constant-speed check, but on f_norm-onset instead of tau_border
    print("=== referee's model on f_norm-onset: activation + distance/speed ===")
    print("seed mass-center radii (voxels, 192^3, R=96): "
          "distributed~0, shell~72, central~0")
    print("NOTE: distributed and central both have small mass-center radius;")
    print("      the discriminating pair is shell (r=72) vs central (r=0).")
    # activation proxy = time to 10% f_norm for distributed (closest to boundary)
    act = norm_table["distributed"].get(0.10)
    if act is not None and np.isfinite(act):
        print(f"activation proxy (distributed time to 10% f_norm): {act:.0f}")
    else:
        print("activation proxy (distributed time to 10% f_norm): n/a")


if __name__ == "__main__":
    main()
