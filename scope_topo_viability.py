#!/usr/bin/env python3
"""
Topology viability check
========================
The (F,k) scan probes only the `central` seed. But the whole experiment
compares three topologies, so the operating point must keep ALL THREE
alive -- otherwise the "topological ordering" in kappa is just an
ordering of which topologies happened to survive, scored against the
gzip floor.

At the SCOPE default (0.060, 0.062) this fails: central survives while
shell and distributed extinguish, and the dead ones score kappa = 0.704
(the floor) against the live one's 0.301 -- i.e. the artifact outranks
the physics and reverses the ordering.

Selection requirement for an operating point:
  - all three topologies alive at t=T (K_exc_inner > 0.02)
  - structure reaches the border (K_exc_border > 0.02)
  - domain NOT saturated (fill < ~0.9), so kappa is not in the
    trivial-parity regime where both regions are equally patterned

Usage:
  python scope_topo_viability.py --grid 96 --steps 20000
"""

import argparse
import json
import os
import time

import torch
import torch.multiprocessing as mp

from scope_fk_scan import probe

CANDIDATES = [
    (0.060, 0.062),   # SCOPE paper default, for reference
    (0.054, 0.062),
    (0.046, 0.060),
    (0.042, 0.062),
    (0.038, 0.058),
    (0.038, 0.062),
    (0.034, 0.062),
    (0.030, 0.055),
]


def _worker(rank, n_gpus, jobs, args, out_q):
    device = torch.device(f"cuda:{rank}" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        torch.cuda.set_device(rank)
    res = []
    for i, (F, k, topo) in enumerate(jobs):
        if i % n_gpus != rank:
            continue
        t0 = time.time()
        d = probe(args.grid, F, k, args, device, topology=topo, seed=1000)
        d["topology"] = topo
        res.append(d)
        print(f"[gpu{rank}] F={F:.3f} k={k:.3f} {topo:12s} "
              f"alive={d['alive']:d} reach={d['reach']:d} fill={d['fill']:.3f} "
              f"Kexc_in={d['K_exc_inner']:.3f} Kexc_bd={d['K_exc_border']:.3f} "
              f"kappa_raw={d['kappa_raw']:.3f} ({time.time()-t0:.0f}s)", flush=True)
    out_q.put(res)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", type=int, default=96)
    p.add_argument("--steps", type=int, default=20000)
    p.add_argument("--Du", type=float, default=0.16)
    p.add_argument("--Dv", type=float, default=0.08)
    p.add_argument("--dt", type=float, default=0.18)
    p.add_argument("--outdir", type=str, default="scan_topo")
    p.add_argument("--gpus", type=int, default=0)
    args = p.parse_args()

    n_gpus = args.gpus or max(1, torch.cuda.device_count())
    os.makedirs(args.outdir, exist_ok=True)
    topos = ["central", "shell", "distributed"]
    jobs = [(F, k, t) for (F, k) in CANDIDATES for t in topos]
    print(f"[viab] {len(jobs)} jobs, grid={args.grid}^3, {n_gpus} GPUs")

    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=(r, n_gpus, jobs, args, q))
             for r in range(n_gpus)]
    t0 = time.time()
    for pr in procs:
        pr.start()
    out = []
    for _ in procs:
        out.extend(q.get())
    for pr in procs:
        pr.join()

    with open(os.path.join(args.outdir, "viability.json"), "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n[viab] done in {(time.time()-t0)/60:.1f} min\n")
    print(f"{'F':>6} {'k':>6} | {'wszystkie zywe':>14} {'wszystkie reach':>15} "
          f"{'max fill':>9} | kappa_raw central/shell/distributed")
    print("-" * 100)
    for (F, k) in CANDIDATES:
        grp = [d for d in out if d["F"] == F and d["k"] == k]
        grp.sort(key=lambda d: topos.index(d["topology"]))
        allv = all(d["alive"] for d in grp)
        allr = all(d["reach"] for d in grp)
        mx = max(d["fill"] for d in grp)
        ks = " / ".join(f"{d['kappa_raw']:.3f}" for d in grp)
        flag = "  <-- KANDYDAT" if (allv and allr and mx < 0.9) else ""
        print(f"{F:6.3f} {k:6.3f} | {str(allv):>14} {str(allr):>15} "
              f"{mx:9.3f} | {ks}{flag}")


if __name__ == "__main__":
    main()
