#!/usr/bin/env python3
"""
SCOPE topology experiment, v2
=============================
Rebuild of the topology experiment after the three defects documented in
FINDINGS.md. Changes relative to scope_topology.py (kept unmodified as
the audit reference):

  1. SEEDING (scope_seed.py). The shell sets the volume budget at a
     diffusively survivable thickness; central and distributed are matched
     to it. The realized voxel counts are recorded per run, so the volume
     control is auditable instead of asserted.

  2. PRIMARY OBSERVABLE is thermodynamic cost, not compressed size
     (scope_thermo.py). kappa_gzip is retained as a secondary channel for
     continuity with the paper, but it cannot separate a dead field from a
     saturated one -- both score ~1 -- whereas the dissipation ratio has a
     true zero and can exceed parity.

  3. SATURATION IS RECORDED (`fill`). kappa near parity is only
     interpretable while fill < 1; once the pattern tiles the domain both
     regions are trivially alike.

  4. LAPLACIAN is conv3d, not the roll-based masked_laplacian
     (scope_laplacian.py) -- an implementation change, not a protocol
     change (CHANGELOG.md, 2026-07-24); the roll-based version in
     scope_topology.py is untouched and remains the v1 audit reference.

First-passage times are reported for both channels:
  tau_gzip : first t with kappa_gzip >= parity   (legacy, comparable to v1)
  tau_diss : first t with diss_ratio  >= parity   (cost-based)

Usage:
  python scope_topology_v2.py --grid 288 --steps 20000 --n-runs 8 \
      --outdir results_v2_x1
"""

import argparse
import json
import os
import time

import numpy as np
import torch
import torch.multiprocessing as mp

from scope_topology import build_masks, K_compress
from scope_laplacian import (build_laplacian_kernel, build_boundary_correction,
                             masked_laplacian_conv3d)
from scope_seed import seed_fields_v2
from scope_thermo import thermo_observables, K_floor_bytes

REC_KEYS = ("t", "kappa_gzip", "kappa_exc", "K_inner", "K_border",
            "K_exc_inner", "K_exc_border", "diss_inner", "diss_border",
            "diss_ratio", "reac_inner", "reac_border", "reac_ratio",
            "diss_total", "v_mass", "fill")


# torch.compile on the Laplacian + Euler step, on by default for CUDA
# (CHANGELOG.md, 2026-07-24). No flag to disable: if compilation or the
# first compiled call raises (e.g. no Triton), fall back to eager for the
# rest of the process rather than aborting the run.
_COMPILE_FAILED = False
_COMPILED_STEP = None


def _euler_step(u, v, lap_kernel, lap_correction, domain, Du, Dv, F, k, dt):
    lap_u = masked_laplacian_conv3d(u, lap_kernel, lap_correction)
    lap_v = masked_laplacian_conv3d(v, lap_kernel, lap_correction)
    uvv = u * v * v
    u = u + dt * (Du * lap_u - uvv + F * (1.0 - u))
    v = v + dt * (Dv * lap_v + uvv - (F + k) * v)
    u = torch.where(domain, u.clamp(0, 1), torch.zeros_like(u))
    v = torch.where(domain, v.clamp(0, 1), torch.zeros_like(v))
    return u, v


def _get_step_fn(device):
    global _COMPILED_STEP
    if device.type != "cuda" or _COMPILE_FAILED:
        return _euler_step
    if _COMPILED_STEP is None:
        _COMPILED_STEP = torch.compile(_euler_step)
    return _COMPILED_STEP


@torch.no_grad()
def run_one_v2(n, topology, seed, args, device):
    domain, inner, border, r, R = build_masks(n, device)
    domain_f = domain.float()
    inner_f = inner.float()
    border_f = border.float()
    rng = np.random.default_rng(seed)
    u, v, _, seed_info = seed_fields_v2(n, topology, rng, domain, r, R, device,
                                        shell_thickness=args.shell_thickness)

    inner_idx = inner.cpu().numpy()
    border_idx = border.cpu().numpy()
    fl_in = K_floor_bytes(int(inner.sum()))
    fl_bd = K_floor_bytes(int(border.sum()))
    Du, Dv, F, k, dt = args.Du, args.Dv, args.F, args.k, args.dt
    n_dom = float(domain.sum().item())

    # conv3d Laplacian (scope_laplacian.py): fixed kernel + boundary
    # correction computed once per grid, replacing 12 torch.roll pairs/step.
    # Equivalence vs the v1 roll-based masked_laplacian is gated by
    # scope_test_laplacian_equivalence.py, not asserted here.
    lap_kernel, _ = build_laplacian_kernel(device, domain_f.dtype)
    lap_correction = build_boundary_correction(domain_f)

    rec = {kk: [] for kk in REC_KEYS}
    step_fn = _get_step_fn(device)

    for step in range(args.steps + 1):
        if step % args.record_every == 0:
            v_np = v.cpu().numpy()
            K_in = K_compress(v_np[inner_idx])
            K_bd = K_compress(v_np[border_idx])
            e_in, e_bd = K_in - fl_in, K_bd - fl_bd
            th = thermo_observables(u, v, domain_f, inner_f, border_f,
                                    Du, Dv, F)
            rec["t"].append(step * dt)
            rec["kappa_gzip"].append(K_bd / K_in if K_in > 1e-12 else float("nan"))
            rec["kappa_exc"].append(e_bd / e_in if e_in > 1e-6 else float("nan"))
            rec["K_inner"].append(K_in)
            rec["K_border"].append(K_bd)
            rec["K_exc_inner"].append(e_in)
            rec["K_exc_border"].append(e_bd)
            for nm in ("diss", "reac"):
                rec[f"{nm}_inner"].append(th[f"{nm}_inner"])
                rec[f"{nm}_border"].append(th[f"{nm}_border"])
                rec[f"{nm}_ratio"].append(th[f"{nm}_ratio"])
            rec["diss_total"].append(th["diss_total"])
            rec["v_mass"].append(th["v_mass"])
            rec["fill"].append(float((v > 0.1).sum().item()) / n_dom)

        try:
            u, v = step_fn(u, v, lap_kernel, lap_correction, domain, Du, Dv, F, k, dt)
        except Exception as e:
            if step_fn is _euler_step:
                raise
            global _COMPILE_FAILED
            _COMPILE_FAILED = True
            print(f"[scope] WARNING: torch.compile failed at step {step} "
                  f"({type(e).__name__}: {e}); falling back to eager "
                  "for the rest of this process", flush=True)
            step_fn = _euler_step
            u, v = step_fn(u, v, lap_kernel, lap_correction, domain, Du, Dv, F, k, dt)

    def first_passage(series):
        for t, x in zip(rec["t"], series):
            if np.isfinite(x) and x >= args.parity:
                return t
        return None

    # Read at t=T, never as a max over the trajectory. A seed that ignites
    # and then extinguishes peaks early: the 2-voxel shell at 192^3 has
    # fill=0.038 at t=0, fill=0 from t=90 onward, and diss_inner(T)=8.2e-15,
    # yet a max-based flag called it alive.
    from scope_thermo import DISS_FLOOR
    alive = rec["diss_inner"][-1] > DISS_FLOOR
    rec.update({
        "topology": topology, "seed": seed, "seed_info": seed_info,
        "tau_gzip": first_passage(rec["kappa_gzip"]),
        "tau_diss": first_passage(rec["diss_ratio"]),
        "alive": bool(alive),
        "diss_ratio_max": float(np.nanmax(rec["diss_ratio"])),
        "fill_max": float(np.max(rec["fill"])),
    })
    return rec


def _worker(rank, n_gpus, jobs, args, out_q):
    device = torch.device(f"cuda:{rank}" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        torch.cuda.set_device(rank)
    res = []
    for i, (topo, seed) in enumerate(jobs):
        if i % n_gpus != rank:
            continue
        t0 = time.time()
        d = run_one_v2(args.grid, topo, seed, args, device)
        d["wall_s"] = time.time() - t0
        d["gpu"] = rank
        res.append(d)
        print(f"[gpu{rank}] {topo:12s} seed={seed} alive={d['alive']:d} "
              f"diss_ratio(T)={d['diss_ratio'][-1]:.4f} "
              f"max={d['diss_ratio_max']:.4f} tau_diss={d['tau_diss']} "
              f"kappa_gzip(T)={d['kappa_gzip'][-1]:.4f} "
              f"fill={d['fill'][-1]:.3f} ({d['wall_s']:.0f}s)", flush=True)
    out_q.put(res)


def summarize(all_runs, args, outdir):
    summary = {}
    for topo in args.topologies:
        runs = [r for r in all_runs if r["topology"] == topo]
        alive = [r for r in runs if r["alive"]]
        dr = np.array([r["diss_ratio"] for r in runs], dtype=float)
        kg = np.array([r["kappa_gzip"] for r in runs], dtype=float)
        td = [r["tau_diss"] for r in runs if r["tau_diss"] is not None]
        tg = [r["tau_gzip"] for r in runs if r["tau_gzip"] is not None]
        summary[topo] = {
            "n_runs": len(runs), "n_alive": len(alive),
            "seeded_fraction": runs[0]["seed_info"]["seeded_fraction"],
            "match_ratio": runs[0]["seed_info"]["match_ratio"],
            "diss_ratio_T_mean": float(np.nanmean(dr[:, -1])),
            "diss_ratio_T_std": float(np.nanstd(dr[:, -1])),
            "diss_ratio_max_mean": float(np.nanmean([r["diss_ratio_max"] for r in runs])),
            "kappa_gzip_T_mean": float(np.nanmean(kg[:, -1])),
            "kappa_gzip_T_std": float(np.nanstd(kg[:, -1])),
            "fill_T_mean": float(np.mean([r["fill"][-1] for r in runs])),
            "tau_diss_mean": float(np.mean(td)) if td else None,
            "tau_diss_std": float(np.std(td)) if td else None,
            "n_passed_diss": len(td),
            "tau_gzip_mean": float(np.mean(tg)) if tg else None,
            "tau_gzip_std": float(np.std(tg)) if tg else None,
            "n_passed_gzip": len(tg),
        }
    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        colors = {"central": "tab:red", "shell": "tab:blue",
                  "distributed": "tab:green"}
        fig, axes = plt.subplots(1, 3, figsize=(17, 4.6))
        for topo in args.topologies:
            runs = [r for r in all_runs if r["topology"] == topo]
            t = np.array(runs[0]["t"])
            c = colors.get(topo)
            for ax, key, lab in (
                    (axes[0], "diss_ratio", "dissipation ratio (border/inner)"),
                    (axes[1], "kappa_gzip", r"$\kappa_{gzip}$"),
                    (axes[2], "fill", "fill fraction")):
                A = np.array([r[key] for r in runs], dtype=float)
                m, s = np.nanmean(A, 0), np.nanstd(A, 0)
                ax.plot(t, m, color=c, label=f"{topo} (n={len(runs)})")
                ax.fill_between(t, m - s, m + s, alpha=0.2, color=c)
                ax.set_xlabel("t")
                ax.set_ylabel(lab)
        axes[0].axhline(args.parity, ls="--", c="gray", lw=1)
        axes[1].axhline(args.parity, ls="--", c="gray", lw=1)
        axes[0].set_title(f"PRIMARY: cost ratio, grid {args.grid}$^3$")
        axes[1].set_title("SECONDARY: gzip kappa (floor-confounded)")
        axes[2].set_title("saturation control")
        axes[0].legend()
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, "topology_v2.png"), dpi=150)
    except ImportError:
        print("[scope] matplotlib not available; skipped plots")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", type=int, default=288)
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
    p.add_argument("--shell-thickness", type=float, default=3.0)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--outdir", type=str, default="results_v2")
    p.add_argument("--gpus", type=int, default=0)
    p.add_argument("--topologies", nargs="+",
                   default=["central", "shell", "distributed"])
    args = p.parse_args()

    n_gpus = args.gpus or max(1, torch.cuda.device_count())
    os.makedirs(args.outdir, exist_ok=True)
    jobs = [(t, args.seed_base + i)
            for t in args.topologies for i in range(args.n_runs)]
    print(f"[v2] grid={args.grid}^3 steps={args.steps} F={args.F} k={args.k} "
          f"shell_th={args.shell_thickness} {len(jobs)} jobs / {n_gpus} GPUs")

    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=(r, n_gpus, jobs, args, q))
             for r in range(n_gpus)]
    t0 = time.time()
    for pr in procs:
        pr.start()
    all_runs = []
    for _ in procs:
        all_runs.extend(q.get())
    for pr in procs:
        pr.join()
        if pr.exitcode != 0:
            raise RuntimeError(f"worker exited {pr.exitcode}")
    wall = time.time() - t0

    order = {t: i for i, t in enumerate(args.topologies)}
    all_runs.sort(key=lambda r: (order[r["topology"]], r["seed"]))
    meta = {"args": vars(args), "n_gpus": n_gpus, "wall_s": wall,
            "torch": torch.__version__}
    with open(os.path.join(args.outdir, "runs.json"), "w") as f:
        json.dump({"meta": meta, "runs": all_runs}, f)

    s = summarize(all_runs, args, args.outdir)
    print(f"\n[v2] {len(all_runs)} runs in {wall/60:.1f} min -> {args.outdir}")
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
