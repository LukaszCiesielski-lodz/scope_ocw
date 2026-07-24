#!/usr/bin/env python3
"""
SCOPE multi-GPU driver
======================
Thin work-distribution wrapper around scope_topology.py. It imports
`run_one` UNCHANGED, so the numerics are bit-identical to the reference
implementation; this file only decides which GPU runs which job and how
the results are aggregated.

Rationale for not batching the ensemble into a leading tensor dimension:
measured on 4x RTX 4090, the 192^3 integration is already memory-bandwidth
bound (B=1: 4.40 ms/step, B=8: 5.35 ms/step/run -- batching is a net
loss). At 96^3 batching helps up to B=4 only. Process-level sharding
gives the full 4x with zero divergence from the reference numerics.

Usage:
  python scope_run.py --grid 96  --steps 20000 --n-runs 8 --outdir results_x1
  python scope_run.py --grid 192 --steps 20000 --n-runs 8 --scale 2 \
      --outdir results_x2

Ensembles can be extended without recomputing: --seed-base is the first
seed, so runs 0..7 of any invocation are the same trajectories as the
reference script's default ensemble.
"""

import argparse
import json
import os
import time

import numpy as np
import torch
import torch.multiprocessing as mp

from scope_topology import run_one


def _worker(rank, n_gpus, jobs, args, out_q):
    """Run this rank's share of the job list on cuda:rank."""
    device = torch.device(f"cuda:{rank}" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        torch.cuda.set_device(rank)
    mine = [j for i, j in enumerate(jobs) if i % n_gpus == rank]
    results = []
    for topo, seed in mine:
        t0 = time.time()
        res = run_one(args.grid, topo, seed=seed, args=args, device=device)
        res["wall_s"] = time.time() - t0
        res["gpu"] = rank
        results.append(res)
        print(f"[gpu{rank}] {topo:12s} seed={seed}: "
              f"kappa(T)={res['kappa'][-1]:.3f} "
              f"tau={res['tau_first_passage']} ({res['wall_s']:.1f}s)",
              flush=True)
    out_q.put(results)


def summarize(all_runs, args, outdir):
    """Ensemble summary + figure. Mirrors scope_topology.py's reporting."""
    summary = {}
    for topo in args.topologies:
        runs = [r for r in all_runs if r["topology"] == topo]
        K = np.array([r["kappa"] for r in runs])
        taus = [r["tau_first_passage"] for r in runs
                if r["tau_first_passage"] is not None]
        summary[topo] = {
            "kappa_T_mean": float(np.nanmean(K[:, -1])),
            "kappa_T_std": float(np.nanstd(K[:, -1])),
            "kappa_T_sem": float(np.nanstd(K[:, -1]) / np.sqrt(len(runs))),
            "kappa_max_mean": float(np.nanmean(np.nanmax(K, axis=1))),
            "tau_mean": float(np.mean(taus)) if taus else None,
            "tau_std": float(np.std(taus)) if taus else None,
            "n_passed": len(taus), "n_runs": len(runs),
        }

    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        colors = {"central": "tab:red", "shell": "tab:blue",
                  "distributed": "tab:green"}
        for topo in args.topologies:
            runs = [r for r in all_runs if r["topology"] == topo]
            t = np.array(runs[0]["t"])
            K = np.array([r["kappa"] for r in runs])
            mean, std = np.nanmean(K, 0), np.nanstd(K, 0)
            c = colors.get(topo)
            axes[0].plot(t, mean, color=c, label=f"{topo} (n={len(runs)})")
            axes[0].fill_between(t, mean - std, mean + std, alpha=0.2, color=c)
            taus = [r["tau_first_passage"] for r in runs
                    if r["tau_first_passage"] is not None]
            if taus:
                axes[1].scatter([topo] * len(taus), taus, alpha=0.6, color=c)
        axes[0].axhline(args.parity, ls="--", c="gray", lw=1)
        axes[0].set_xlabel("t")
        axes[0].set_ylabel(r"$\kappa(t)$")
        axes[0].set_title(rf"$\kappa(t)$ mean $\pm$ std, grid {args.grid}$^3$")
        axes[0].legend()
        axes[1].set_ylabel(r"$\tau$ (first passage)")
        axes[1].set_title("First-passage times")
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, "kappa_topologies.png"), dpi=150)
    except ImportError:
        print("[scope] matplotlib not available; skipped plots")

    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", type=int, default=96)
    p.add_argument("--steps", type=int, default=20000)
    p.add_argument("--record-every", type=int, default=200)
    p.add_argument("--n-runs", type=int, default=8)
    p.add_argument("--seed-base", type=int, default=1000)
    p.add_argument("--F", type=float, default=0.06)
    p.add_argument("--k", type=float, default=0.062)
    p.add_argument("--Du", type=float, default=0.16)
    p.add_argument("--Dv", type=float, default=0.08)
    p.add_argument("--dt", type=float, default=0.18)
    p.add_argument("--parity", type=float, default=1.0)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--outdir", type=str, default="results")
    p.add_argument("--gpus", type=int, default=0, help="0 = use all visible")
    p.add_argument("--topologies", nargs="+",
                   default=["central", "shell", "distributed"])
    args = p.parse_args()

    n_gpus = args.gpus or max(1, torch.cuda.device_count())
    os.makedirs(args.outdir, exist_ok=True)

    jobs = [(topo, args.seed_base + i)
            for topo in args.topologies
            for i in range(args.n_runs)]
    print(f"[scope] grid={args.grid}^3 steps={args.steps} "
          f"{len(jobs)} jobs over {n_gpus} GPU(s)")

    t0 = time.time()
    ctx = mp.get_context("spawn")
    out_q = ctx.Queue()
    procs = [ctx.Process(target=_worker,
                         args=(r, n_gpus, jobs, args, out_q))
             for r in range(n_gpus)]
    for pr in procs:
        pr.start()
    all_runs = []
    for _ in procs:
        all_runs.extend(out_q.get())
    for pr in procs:
        pr.join()
        if pr.exitcode != 0:
            raise RuntimeError(f"worker exited with code {pr.exitcode}")
    wall = time.time() - t0

    # deterministic ordering, independent of which GPU finished first
    order = {t: i for i, t in enumerate(args.topologies)}
    all_runs.sort(key=lambda r: (order[r["topology"]], r["seed"]))

    meta = {"args": vars(args), "n_gpus": n_gpus, "wall_s": wall,
            "torch": torch.__version__,
            "device_name": torch.cuda.get_device_name(0)
            if torch.cuda.is_available() else "cpu"}
    with open(os.path.join(args.outdir, "runs.json"), "w") as f:
        json.dump({"meta": meta, "runs": all_runs}, f)

    summary = summarize(all_runs, args, args.outdir)
    print(f"[scope] {len(all_runs)} runs in {wall/60:.1f} min -> {args.outdir}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
