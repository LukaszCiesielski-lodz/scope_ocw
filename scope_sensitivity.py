#!/usr/bin/env python3
"""
(F,k) sensitivity yardstick
===========================
CRITERIA_v2.md requires a between-topology effect to exceed the spread
that perturbing the CONTROL PARAMETERS alone produces. Without this
reference, "the difference is above noise" means only "above run-to-run
scatter at fixed parameters", which is the weaker claim -- and is how the
original paper reported a geometry difference of 0.005 while the (F,k)
sensitivity of the same quantity was ~0.15, i.e. 30x larger.

Holds the topology fixed and perturbs (F,k) by +-pct, one run per point,
same seed. The reported spread is the yardstick.

Must be run at the SAME grid and step count as the main experiment,
otherwise the comparison is not like-for-like.

Usage:
  python scope_sensitivity.py --grid 288 --steps 60000 --F 0.042 --k 0.062 \
      --topology central --outdir sens_288
"""

import argparse
import json
import os
import time

import numpy as np
import torch
import torch.multiprocessing as mp

from scope_topology_v2 import run_one_v2
from scope_analyze import tau_border


def _worker(rank, n_gpus, jobs, args, out_q):
    device = torch.device(f"cuda:{rank}" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        torch.cuda.set_device(rank)
    res = []
    for i, (F, k) in enumerate(jobs):
        if i % n_gpus != rank:
            continue
        a = argparse.Namespace(**vars(args))
        a.F, a.k = F, k
        t0 = time.time()
        d = run_one_v2(args.grid, args.topology, args.seed, a, device)
        # the yardstick must be measured on the PRIMARY observable
        tb = tau_border(d)
        rec = {"F": F, "k": k,
               "tau_border": tb,
               "diss_ratio_T": d["diss_ratio"][-1],
               "kappa_gzip_T": d["kappa_gzip"][-1],
               "fill_T": d["fill"][-1],
               "alive": d["alive"]}
        res.append(rec)
        print(f"[gpu{rank}] F={F:.5f} k={k:.5f} alive={rec['alive']:d} "
              f"tau_border={tb} diss_ratio(T)={rec['diss_ratio_T']:.4f} "
              f"fill={rec['fill_T']:.3f} ({time.time()-t0:.0f}s)", flush=True)
    out_q.put(res)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", type=int, default=288)
    p.add_argument("--steps", type=int, default=60000)
    p.add_argument("--record-every", type=int, default=500)
    p.add_argument("--F", type=float, default=0.042)
    p.add_argument("--k", type=float, default=0.062)
    p.add_argument("--pct", type=float, default=2.0, help="perturbacja w %")
    p.add_argument("--Du", type=float, default=0.16)
    p.add_argument("--Dv", type=float, default=0.08)
    p.add_argument("--dt", type=float, default=0.18)
    p.add_argument("--parity", type=float, default=1.0)
    p.add_argument("--shell-thickness", type=float, default=3.0)
    p.add_argument("--topology", type=str, default="central")
    p.add_argument("--seed", type=int, default=1000)
    p.add_argument("--outdir", type=str, default="sens")
    p.add_argument("--gpus", type=int, default=0)
    args = p.parse_args()

    n_gpus = args.gpus or max(1, torch.cuda.device_count())
    os.makedirs(args.outdir, exist_ok=True)
    f = args.pct / 100.0
    jobs = [(args.F * (1 + a), args.k * (1 + b))
            for a in (-f, 0.0, f) for b in (-f, 0.0, f)]
    print(f"[sens] topologia={args.topology} baza=({args.F},{args.k}) "
          f"+-{args.pct}% -> {len(jobs)} punktow / {n_gpus} GPU")

    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=(r, n_gpus, jobs, args, q))
             for r in range(n_gpus)]
    for pr in procs:
        pr.start()
    out = []
    for _ in procs:
        out.extend(q.get())
    for pr in procs:
        pr.join()

    tb = np.array([d["tau_border"] for d in out
                   if d["alive"] and d["tau_border"] is not None], dtype=float)
    dr = np.array([d["diss_ratio_T"] for d in out
                   if d["alive"] and np.isfinite(d["diss_ratio_T"])])
    res = {
        "base": {"F": args.F, "k": args.k}, "pct": args.pct,
        "topology": args.topology, "grid": args.grid, "steps": args.steps,
        "n_alive": int(sum(d["alive"] for d in out)), "n_points": len(out),
        "n_tau": int(len(tb)),
        # PRIMARY yardstick: spread of tau_border under (F,k) perturbation
        "tau_border_spread": float(tb.max() - tb.min()) if len(tb) else None,
        "tau_border_std": float(tb.std()) if len(tb) else None,
        "tau_border_median": float(np.median(tb)) if len(tb) else None,
        # secondary, descriptive only
        "diss_ratio_spread": float(dr.max() - dr.min()) if len(dr) else None,
        "points": out,
    }
    with open(os.path.join(args.outdir, "sensitivity.json"), "w") as f_:
        json.dump(res, f_, indent=2)
    print(f"\n[sens] zywych {res['n_alive']}/{res['n_points']}, "
          f"z tau_border {res['n_tau']}")
    print(f"[sens] GLOWNA: rozrzut tau_border przy +-{args.pct}% w (F,k): "
          f"{res['tau_border_spread']} (mediana {res['tau_border_median']})")
    print(f"[sens] (drugorzedne) rozrzut diss_ratio(T): "
          f"{res['diss_ratio_spread']}")
    print(f"[sens] -> {args.outdir}/sensitivity.json")


if __name__ == "__main__":
    main()
