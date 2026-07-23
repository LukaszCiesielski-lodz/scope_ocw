#!/usr/bin/env python3
"""
(F,k) viability scan
====================
The SCOPE default (F=0.06, k=0.062) clears the Gray-Scott existence
condition F >= 4(F+k)^2 by only 0.78%, and empirically the pattern
extinguishes for the shell and distributed topologies (K collapses to the
gzip uniform-field floor by t~360). Any kappa measured after that is a
property of gzip's header overhead, not of the dynamics.

This scan locates (F,k) where the pattern (a) survives to the end of the
run and (b) actually propagates into the border shell, so that kappa
measures export rather than compressor overhead.

Diagnostics per point, all floor-corrected:
  alive      : K_inner stays above the uniform-field floor at t=T
  reach      : K_border above floor at t=T (structure got to the boundary)
  fill       : fraction of domain voxels with v > 0.1
  K_exc_*    : floor-corrected complexity, (K - K_floor(N))

Usage:
  python scope_fk_scan.py --grid 96 --steps 20000 --outdir scan_fk
"""

import argparse
import json
import os
import time

import numpy as np
import torch
import torch.multiprocessing as mp

from scope_topology import build_masks, masked_laplacian, seed_fields, K_compress


def K_floor(n_voxels: int) -> float:
    """gzip cost per voxel of a perfectly uniform region of this size.

    This is the value K_compress returns for any constant field, so it is
    the artifact baseline that must be subtracted before kappa means
    anything.
    """
    if n_voxels == 0:
        return 0.0
    return K_compress(np.zeros(n_voxels, dtype=np.float32))


@torch.no_grad()
def probe(n, F, k, args, device, topology="central", seed=1000):
    domain, inner, border, r, R = build_masks(n, device)
    domain_f = domain.float()
    rng = np.random.default_rng(seed)
    u, v, _ = seed_fields(n, topology, rng, domain, r, R, device)
    inner_idx = inner.cpu().numpy()
    border_idx = border.cpu().numpy()
    fl_in = K_floor(int(inner.sum()))
    fl_bd = K_floor(int(border.sum()))
    Du, Dv, dt = args.Du, args.Dv, args.dt

    for step in range(args.steps):
        lap_u = masked_laplacian(u, domain_f)
        lap_v = masked_laplacian(v, domain_f)
        uvv = u * v * v
        u = u + dt * (Du * lap_u - uvv + F * (1.0 - u))
        v = v + dt * (Dv * lap_v + uvv - (F + k) * v)
        u = torch.where(domain, u.clamp(0, 1), torch.zeros_like(u))
        v = torch.where(domain, v.clamp(0, 1), torch.zeros_like(v))

    v_np = v.cpu().numpy()
    K_in = K_compress(v_np[inner_idx])
    K_bd = K_compress(v_np[border_idx])
    fill = float((v > 0.1).sum().item() / domain.sum().item())
    return {
        "F": F, "k": k,
        "margin": float((F - 4 * (F + k) ** 2) / (4 * (F + k) ** 2)),
        "K_inner": K_in, "K_border": K_bd,
        "K_exc_inner": K_in - fl_in, "K_exc_border": K_bd - fl_bd,
        "kappa_raw": K_bd / K_in if K_in > 1e-12 else float("nan"),
        "floor_kappa": fl_bd / fl_in,
        "fill": fill,
        "v_max": float(v.max().item()),
        "alive": bool(K_in - fl_in > 0.02),
        "reach": bool(K_bd - fl_bd > 0.02),
    }


def _worker(rank, n_gpus, points, args, out_q):
    device = torch.device(f"cuda:{rank}" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        torch.cuda.set_device(rank)
    res = []
    for i, (F, k) in enumerate(points):
        if i % n_gpus != rank:
            continue
        t0 = time.time()
        d = probe(args.grid, F, k, args, device)
        res.append(d)
        print(f"[gpu{rank}] F={F:.4f} k={k:.4f} margin={d['margin']*100:+6.2f}% "
              f"alive={d['alive']:d} reach={d['reach']:d} fill={d['fill']:.3f} "
              f"Kexc_in={d['K_exc_inner']:.4f} ({time.time()-t0:.0f}s)", flush=True)
    out_q.put(res)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", type=int, default=96)
    p.add_argument("--steps", type=int, default=20000)
    p.add_argument("--Du", type=float, default=0.16)
    p.add_argument("--Dv", type=float, default=0.08)
    p.add_argument("--dt", type=float, default=0.18)
    p.add_argument("--outdir", type=str, default="scan_fk")
    p.add_argument("--gpus", type=int, default=0)
    args = p.parse_args()

    n_gpus = args.gpus or max(1, torch.cuda.device_count())
    os.makedirs(args.outdir, exist_ok=True)

    Fs = [0.020, 0.026, 0.030, 0.034, 0.038, 0.042, 0.046, 0.054, 0.060]
    ks = [0.048, 0.052, 0.055, 0.058, 0.060, 0.062, 0.065]
    points = [(F, k) for F in Fs for k in ks]
    print(f"[scan] {len(points)} points, grid={args.grid}^3, "
          f"steps={args.steps}, {n_gpus} GPUs")

    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=(r, n_gpus, points, args, q))
             for r in range(n_gpus)]
    t0 = time.time()
    for pr in procs:
        pr.start()
    out = []
    for _ in procs:
        out.extend(q.get())
    for pr in procs:
        pr.join()
    out.sort(key=lambda d: (d["F"], d["k"]))

    with open(os.path.join(args.outdir, "scan.json"), "w") as f:
        json.dump({"args": vars(args), "points": out}, f, indent=2)

    print(f"\n[scan] done in {(time.time()-t0)/60:.1f} min\n")
    print("Kandydaci (alive AND reach), wg zapasu K ponad podloga:")
    good = [d for d in out if d["alive"] and d["reach"]]
    good.sort(key=lambda d: -min(d["K_exc_inner"], d["K_exc_border"]))
    for d in good[:15]:
        print(f"  F={d['F']:.3f} k={d['k']:.3f} margin={d['margin']*100:+6.2f}% "
              f"fill={d['fill']:.3f} Kexc_in={d['K_exc_inner']:.4f} "
              f"Kexc_bd={d['K_exc_border']:.4f} kappa_raw={d['kappa_raw']:.3f}")
    if not good:
        print("  BRAK -- zaden punkt nie utrzymal struktury do konca przebiegu")


if __name__ == "__main__":
    main()
