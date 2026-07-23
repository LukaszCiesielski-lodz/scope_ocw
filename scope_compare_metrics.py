#!/usr/bin/env python3
"""
Side-by-side: gzip kappa vs thermodynamic-cost observables
==========================================================
Runs the three seed topologies and records, on the same trajectories,
both the original kappa = K_border/K_inner and the cost-based
observables from scope_thermo.py.

The question this answers: does charging for structure make "dead" and
"saturated" separable, where kappa_gzip collapses them both onto ~1?

Usage:
  python scope_compare_metrics.py --grid 96 --steps 20000 --outdir cmp_metrics
"""

import argparse
import json
import os
import time

import numpy as np
import torch
import torch.multiprocessing as mp

from scope_topology import build_masks, masked_laplacian, seed_fields, K_compress
from scope_thermo import thermo_observables, K_floor_bytes

PARAM_SETS = [
    (0.060, 0.062),   # SCOPE default (marginal; shell+distributed die)
    (0.046, 0.060),   # viable, propagating, near-saturating
    (0.042, 0.062),   # viable, propagating, not saturated
]


@torch.no_grad()
def run_traj(n, F, k, topology, seed, args, device):
    domain, inner, border, r, R = build_masks(n, device)
    domain_f = domain.float()
    inner_f = inner.float()
    border_f = border.float()
    rng = np.random.default_rng(seed)
    u, v, _ = seed_fields(n, topology, rng, domain, r, R, device)

    inner_idx = inner.cpu().numpy()
    border_idx = border.cpu().numpy()
    fl_in = K_floor_bytes(int(inner.sum()))
    fl_bd = K_floor_bytes(int(border.sum()))
    Du, Dv, dt = args.Du, args.Dv, args.dt
    n_dom = float(domain.sum().item())

    rec = {kk: [] for kk in
           ("t", "kappa_gzip", "K_inner", "K_border", "K_exc_inner",
            "K_exc_border", "kappa_exc", "diss_inner", "diss_border",
            "diss_ratio", "reac_inner", "reac_border", "reac_ratio",
            "diss_total", "v_mass", "fill")}

    for step in range(args.steps + 1):
        if step % args.record_every == 0:
            v_np = v.cpu().numpy()
            K_in = K_compress(v_np[inner_idx])
            K_bd = K_compress(v_np[border_idx])
            e_in, e_bd = K_in - fl_in, K_bd - fl_bd
            th = thermo_observables(u, v, domain_f, inner_f, border_f, Du, Dv, F)
            rec["t"].append(step * dt)
            rec["kappa_gzip"].append(K_bd / K_in if K_in > 1e-12 else float("nan"))
            rec["K_inner"].append(K_in)
            rec["K_border"].append(K_bd)
            rec["K_exc_inner"].append(e_in)
            rec["K_exc_border"].append(e_bd)
            rec["kappa_exc"].append(e_bd / e_in if e_in > 1e-6 else float("nan"))
            for nm in ("diss", "reac"):
                rec[f"{nm}_inner"].append(th[f"{nm}_inner"])
                rec[f"{nm}_border"].append(th[f"{nm}_border"])
                rec[f"{nm}_ratio"].append(th[f"{nm}_ratio"])
            rec["diss_total"].append(th["diss_total"])
            rec["v_mass"].append(th["v_mass"])
            rec["fill"].append(float((v > 0.1).sum().item()) / n_dom)

        lap_u = masked_laplacian(u, domain_f)
        lap_v = masked_laplacian(v, domain_f)
        uvv = u * v * v
        u = u + dt * (Du * lap_u - uvv + F * (1.0 - u))
        v = v + dt * (Dv * lap_v + uvv - (F + k) * v)
        u = torch.where(domain, u.clamp(0, 1), torch.zeros_like(u))
        v = torch.where(domain, v.clamp(0, 1), torch.zeros_like(v))

    rec.update({"F": F, "k": k, "topology": topology, "seed": seed})
    return rec


def _worker(rank, n_gpus, jobs, args, out_q):
    device = torch.device(f"cuda:{rank}" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        torch.cuda.set_device(rank)
    res = []
    for i, (F, k, topo, seed) in enumerate(jobs):
        if i % n_gpus != rank:
            continue
        t0 = time.time()
        d = run_traj(args.grid, F, k, topo, seed, args, device)
        res.append(d)
        print(f"[gpu{rank}] F={F:.3f} k={k:.3f} {topo:12s} "
              f"kappa_gzip={d['kappa_gzip'][-1]:.3f} "
              f"diss_in={d['diss_inner'][-1]:.3e} "
              f"diss_bd={d['diss_border'][-1]:.3e} "
              f"fill={d['fill'][-1]:.3f} ({time.time()-t0:.0f}s)", flush=True)
    out_q.put(res)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", type=int, default=96)
    p.add_argument("--steps", type=int, default=20000)
    p.add_argument("--record-every", type=int, default=200)
    p.add_argument("--Du", type=float, default=0.16)
    p.add_argument("--Dv", type=float, default=0.08)
    p.add_argument("--dt", type=float, default=0.18)
    p.add_argument("--outdir", type=str, default="cmp_metrics")
    p.add_argument("--gpus", type=int, default=0)
    args = p.parse_args()

    n_gpus = args.gpus or max(1, torch.cuda.device_count())
    os.makedirs(args.outdir, exist_ok=True)
    topos = ["central", "shell", "distributed"]
    jobs = [(F, k, t, 1000) for (F, k) in PARAM_SETS for t in topos]
    print(f"[cmp] {len(jobs)} jobs on {n_gpus} GPUs")

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

    with open(os.path.join(args.outdir, "compare.json"), "w") as f:
        json.dump(out, f)

    print("\n" + "=" * 104)
    print("Stan koncowy (t=T). 'martwy' = brak struktury; 'nasycony' = fill -> 1")
    print("=" * 104)
    print(f"{'F':>6} {'k':>6} {'topologia':>12} | {'kappa_gzip':>10} "
          f"{'kappa_exc':>10} | {'diss_in':>10} {'diss_bd':>10} {'diss_ratio':>10} "
          f"| {'fill':>6}")
    print("-" * 104)
    for (F, k) in PARAM_SETS:
        for t in topos:
            d = next(x for x in out if x["F"] == F and x["k"] == k
                     and x["topology"] == t)
            print(f"{F:6.3f} {k:6.3f} {t:>12} | {d['kappa_gzip'][-1]:10.4f} "
                  f"{d['kappa_exc'][-1]:10.4f} | {d['diss_inner'][-1]:10.3e} "
                  f"{d['diss_border'][-1]:10.3e} {d['diss_ratio'][-1]:10.4f} "
                  f"| {d['fill'][-1]:6.3f}")
        print("-" * 104)


if __name__ == "__main__":
    main()
