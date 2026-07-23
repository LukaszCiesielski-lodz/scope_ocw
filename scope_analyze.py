#!/usr/bin/env python3
"""
Verdict under CRITERIA_v2.md (frozen 2026-07-23)
================================================
Order of operations is fixed by the criteria and must not be reordered:

  1. validity gates B1-B4        -- a failing arm is invalid, not a result
  2. tau_border at the 10% threshold, right-censored at the horizon
  3. log-rank on Kaplan-Meier curves, pairwise, Holm across 3 pairs x 2 sizes
  4. sensitivity yardstick       -- effect must exceed (F,k) perturbation
  5. verdict: CONFIRMED / NEGATIVE / INCONCLUSIVE, disjoint

Mann-Whitney is NOT the test. tau_border is right-censored at a common
horizon and MW has no rank for a non-event; it appears only as a
cross-check where censoring is absent.

Pilot runs do not adjudicate. Only a confirmatory set on fresh seeds may
produce a CONFIRMED verdict; the analyzer refuses to issue one otherwise.

Usage:
  python scope_analyze.py --primary results_conf_288 --control results_conf_192
  python scope_analyze.py --primary viab288_fixed_60k --pilot   # inspect only
"""

import argparse
import itertools
import json
import os

import numpy as np

from scope_survival import (km_curve, logrank_pair, holm, curves_overlap,
                            mannwhitney_crosscheck)

TOPOS = ["central", "shell", "distributed"]
TAU_FRAC = 0.10          # frozen: primary threshold, 10% of final value
DISS_FLOOR = 1e-8


def load(outdir):
    with open(os.path.join(outdir, "runs.json")) as f:
        d = json.load(f)
    return d["meta"], d["runs"]


def tau_border(run, frac=TAU_FRAC):
    """First time diss_border reaches `frac` of its own final value.

    Returns None when the boundary is never reached -> right-censored.
    """
    db = np.asarray(run["diss_border"], dtype=float)
    t = np.asarray(run["t"], dtype=float)
    final = db[-1]
    if not np.isfinite(final) or final <= DISS_FLOOR:
        return None
    hit = np.nonzero(db >= frac * final)[0]
    return float(t[hit[0]]) if len(hit) else None


def gates(runs):
    """B1-B4, all read at t=T, the timepoint the observable is scored at."""
    rep = {}
    for topo in TOPOS:
        arm = [r for r in runs if r["topology"] == topo]
        if not arm:
            continue
        di_T = np.array([r["diss_inner"][-1] for r in arm], dtype=float)
        fill_T = np.array([r["fill"][-1] for r in arm], dtype=float)
        mr = np.array([r["seed_info"]["match_ratio"] for r in arm], dtype=float)
        seeded_in_border = [r["seed_info"].get("seeded_in_border", 0)
                            for r in arm]
        n_dead = int(np.sum(di_T <= DISS_FLOOR))
        rep[topo] = {
            "n": len(arm),
            "B1_alive": bool(np.all(di_T > DISS_FLOOR)),
            "B2_unsaturated": bool(np.all(fill_T < 0.9)),
            "B3_seed_matched": bool(np.all(np.abs(mr - 1.0) < 0.01)),
            "B4_clean_region": bool(all(s == 0 for s in seeded_in_border)),
            "frac_dead": n_dead / len(arm),
            "fill_T_max": float(np.max(fill_T)),
            "match_ratio": float(np.mean(mr)),
            "seeded_fraction": float(arm[0]["seed_info"]["seeded_fraction"]),
        }
        rep[topo]["VALID"] = all(rep[topo][k] for k in
                                 ("B1_alive", "B2_unsaturated",
                                  "B3_seed_matched", "B4_clean_region"))
    return rep


def arm_taus(runs, topo):
    return [tau_border(r) for r in runs if r["topology"] == topo]


def horizon_of(runs):
    return float(np.max([r["t"][-1] for r in runs]))


def threshold_stability(runs, fracs=(0.01, 0.05, 0.10, 0.25, 0.50)):
    """Secondary diagnostic: is the ordering robust to the threshold choice?"""
    rows, orderings = [], []
    for f in fracs:
        med = {}
        for topo in TOPOS:
            vals = [v for v in
                    [tau_border(r, f) for r in runs if r["topology"] == topo]
                    if v is not None]
            med[topo] = float(np.median(vals)) if vals else None
        present = [t for t in TOPOS if med[t] is not None]
        order = tuple(sorted(present, key=lambda t: med[t]))
        rows.append((f, med, order))
        orderings.append(order)
    return rows, len(set(orderings)) == 1


def analyze_set(name, outdir):
    meta, runs = load(outdir)
    g = meta.get("args", {})
    val = gates(runs)
    H = horizon_of(runs)
    taus = {t: arm_taus(runs, t) for t in TOPOS}
    kms = {t: km_curve([x if x is not None else H for x in taus[t]],
                       [x is not None for x in taus[t]], H)
           for t in TOPOS if taus[t]}
    return {"name": name, "outdir": outdir, "meta": meta, "args": g,
            "runs": runs, "gates": val, "horizon": H, "taus": taus,
            "kms": kms}


def print_set(S):
    g = S["args"]
    print(f"\n=== {S['name']}: {S['outdir']} ===")
    print(f"grid={g.get('grid')}^3 steps={g.get('steps')} F={g.get('F')} "
          f"k={g.get('k')} n_runs={g.get('n_runs')} seed_base={g.get('seed_base')} "
          f"horyzont T={S['horizon']:.0f}")
    print("  bramki:")
    for topo, d in S["gates"].items():
        mark = "WAZNE " if d["VALID"] else "NIEWAZNE"
        print(f"    {topo:12s} n={d['n']} [{mark}] B1={d['B1_alive']:d} "
              f"B2={d['B2_unsaturated']:d} B3={d['B3_seed_matched']:d} "
              f"B4={d['B4_clean_region']:d} | martwych={100*d['frac_dead']:.0f}% "
              f"fill={d['fill_T_max']:.3f} frakcja={100*d['seeded_fraction']:.2f}%")
    print("  tau_border (prog 10% wart. koncowej), cenzura na horyzoncie:")
    for topo in TOPOS:
        tv = S["taus"].get(topo, [])
        if not tv:
            continue
        ev = [x for x in tv if x is not None]
        nc = sum(x is None for x in tv)
        med = f"{np.median(ev):.0f}" if ev else "brak"
        print(f"    {topo:12s} mediana={med:>8s}  zdarzen={len(ev)}/{len(tv)} "
              f"cenzurowanych={nc}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", required=True, help="rozmiar podstawowy")
    ap.add_argument("--control", default=None, help="rozmiar kontrolny")
    ap.add_argument("--yardstick", default=None, help="sensitivity.json")
    ap.add_argument("--pilot", action="store_true",
                    help="dane pilotazowe — tylko oglad, bez werdyktu")
    ap.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args()

    sets = [analyze_set("PODSTAWOWY", args.primary)]
    if args.control:
        sets.append(analyze_set("KONTROLNY", args.control))
    for S in sets:
        print_set(S)

    # ---- log-rank, wszystkie pary x wszystkie rozmiary, korekta Holma ----
    print("\n--- log-rank (Mantel-Cox) na krzywych Kaplana-Meiera ---")
    comps = []
    for S in sets:
        for a, b in itertools.combinations(TOPOS, 2):
            va = S["gates"].get(a, {}).get("VALID")
            vb = S["gates"].get(b, {}).get("VALID")
            if not (va and vb):
                comps.append({"set": S["name"], "pair": f"{a} vs {b}",
                              "p": None, "skip": "ramie nieważne"})
                continue
            r = logrank_pair(S["taus"][a], S["taus"][b], S["horizon"])
            ev_a = [x for x in S["taus"][a] if x is not None]
            ev_b = [x for x in S["taus"][b] if x is not None]
            comps.append({
                "set": S["name"], "pair": f"{a} vs {b}",
                "p": r["p"], "chi2": r["chi2"], "n_cens": r["n_cens"],
                "med_a": float(np.median(ev_a)) if ev_a else None,
                "med_b": float(np.median(ev_b)) if ev_b else None,
                "mw": mannwhitney_crosscheck(S["taus"][a], S["taus"][b]),
                "overlap": curves_overlap(S["kms"][a], S["kms"][b])
                if a in S["kms"] and b in S["kms"] else None,
            })
    adj = holm([c["p"] for c in comps])
    for c, pa in zip(comps, adj):
        c["p_holm"] = pa

    print(f"  korekta Holma na {sum(c['p'] is not None for c in comps)} "
          f"porownaniach, alpha={args.alpha}")
    for c in comps:
        if c["p"] is None:
            print(f"  [{c['set'][:4]}] {c['pair']:28s} POMINIETE: {c['skip']}")
            continue
        sig = "*" if c["p_holm"] < args.alpha else " "
        mw = c["mw"].get("p")
        mws = f"MW p={mw:.3g}" if mw is not None else "MW n/d (cenzura)"
        print(f"  [{c['set'][:4]}] {c['pair']:28s} med {c['med_a']:>7.0f} vs "
              f"{c['med_b']:>7.0f} | chi2={c['chi2']:6.2f} p={c['p']:.3e} "
              f"p_Holm={c['p_holm']:.3e} {sig} | cenz={c['n_cens']} "
              f"CI_overlap={c['overlap']} | {mws}")

    # ---- diagnostyka drugorzedna ----
    print("\n--- (drugorzedne) stabilnosc uporzadkowania wzgledem progu ---")
    for S in sets:
        rows, stable = threshold_stability(S["runs"])
        print(f"  [{S['name']}] {'STABILNE' if stable else 'NIESTABILNE'}")
        for f, med, order in rows:
            cells = "  ".join(f"{t}={med[t]:.0f}" if med[t] is not None
                              else f"{t}=brak" for t in TOPOS)
            print(f"     prog={100*f:5.1f}% | {cells}  -> {' < '.join(order)}")

    # ---- miarka wrazliwosci ----
    spread = None
    if args.yardstick and os.path.exists(args.yardstick):
        with open(args.yardstick) as f:
            spread = json.load(f).get("tau_border_spread")
        print(f"\n--- miarka wrazliwosci (F,k) +-2%: rozrzut tau_border = "
              f"{spread} ---")
    elif args.yardstick:
        print(f"\n[uwaga] brak pliku miarki: {args.yardstick}")

    # ---- werdykt ----
    print("\n" + "=" * 78)
    if args.pilot:
        print("DANE PILOTAZOWE — bez werdyktu.")
        print("CRITERIA_v2 §0: pilot sluzy do wyboru obserwabli i punktu")
        print("pracy, nie do orzekania. Wnioski maja status 'sugeruje'.")
        print("=" * 78)
        return

    tested = [c for c in comps if c["p"] is not None]
    if not tested:
        print("WERDYKT: NIEROZSTRZYGNIETE — brak wazliwych porownan.")
        print("=" * 78)
        return

    prim = [c for c in tested if c["set"] == "PODSTAWOWY"]
    ctrl = [c for c in tested if c["set"] == "KONTROLNY"]
    sig_prim = [c for c in prim if c["p_holm"] < args.alpha]
    max_dead = max((d["frac_dead"] for S in sets
                    for d in S["gates"].values()), default=0.0)

    # kierunek uporzadkowania musi sie replikowac miedzy rozmiarami
    def direction(c):
        return np.sign(c["med_a"] - c["med_b"])
    dirs_match = None
    if ctrl:
        dmap = {c["pair"]: direction(c) for c in ctrl}
        dirs_match = all(direction(c) == dmap.get(c["pair"])
                         for c in sig_prim if c["pair"] in dmap)

    grey_p = any(args.alpha <= c["p_holm"] < 0.15 for c in tested)
    all_overlap = all(c["overlap"] for c in tested if c["overlap"] is not None)

    if max_dead > 0.25:
        print(f"WERDYKT: NIEROZSTRZYGNIETE — {100*max_dead:.0f}% przebiegow w "
              f"ramieniu bez dynamiki (prog 25%).")
    elif sig_prim and ctrl and dirs_match and not grey_p:
        print("WERDYKT: POTWIERDZONE (warunkowo — sprawdz miarke wrazliwosci)")
        for c in sig_prim:
            print(f"  {c['pair']}: p_Holm={c['p_holm']:.3e}, kierunek "
                  f"replikuje sie na rozmiarze kontrolnym")
        if spread is None:
            print("  UWAGA: brak miarki wrazliwosci — warunek 'efekt powyzej")
            print("  rozrzutu parametrycznego' NIESPRAWDZONY. Werdykt niepelny.")
    elif not sig_prim and not [c for c in ctrl if c["p_holm"] < args.alpha] \
            and all_overlap:
        print("WERDYKT: NEGATYWNE — brak istotnosci na obu rozmiarach ORAZ")
        print("pasma ufnosci KM przekrywaja sie na calej dlugosci dla")
        print("wszystkich par (aktywnie pokazana rownowaznosc).")
    else:
        print("WERDYKT: NIEROZSTRZYGNIETE")
        if sig_prim and not ctrl:
            print("  istotnosc na rozmiarze podstawowym, brak rozmiaru "
                  "kontrolnego — kierunek nie zreplikowany")
        if sig_prim and ctrl and dirs_match is False:
            print("  istotnosc nie replikuje kierunku miedzy rozmiarami")
        if grey_p:
            print("  p po korekcie w pasmie 0.05-0.15")
        if not sig_prim and not all_overlap:
            print("  brak istotnosci, ale pasma CI sie nie przekrywaja — "
                  "rownowaznosc NIE zostala pokazana")
    print("=" * 78)


if __name__ == "__main__":
    main()
