#!/usr/bin/env python3
"""
Speedup benchmark: roll-based masked_laplacian (v1/scope_topology.py) vs
conv3d masked_laplacian (scope_laplacian.py), on the actual GS step loop
(2 Laplacians + reaction update + clamp per step, matching production).

Run this on the GPU target (Kaggle T4) -- CPU numbers are not the
deliverable metric, only useful as a sanity check that both paths execute.
Must be run AFTER scope_test_laplacian_equivalence.py passes; a speedup
number from a Laplacian that hasn't been checked for correctness is not
evidence of anything.

Usage (the mandated check, before push):
  python scope_bench_laplacian.py --grid 192 --steps 2000

If the reported speedup is below 3x, add --compile to also time
torch.compile on the conv3d step (only reach for this if plain conv3d
alone doesn't clear 3x, per instructions -- compiling is a second lever,
not the first one).
"""

import argparse
import time

import numpy as np
import torch

from scope_topology import build_masks, masked_laplacian
from scope_seed import seed_fields_v2
from scope_laplacian import (build_laplacian_kernel, build_boundary_correction,
                             masked_laplacian_conv3d)


def sync(device):
    if device.type == "cuda":
        torch.cuda.synchronize()


def time_loop(step_fn, u, v, steps, warmup, device):
    for _ in range(warmup):
        u, v = step_fn(u, v)
    sync(device)
    t0 = time.time()
    for _ in range(steps):
        u, v = step_fn(u, v)
    sync(device)
    return time.time() - t0, u, v


def make_old_step(domain, domain_f, Du, Dv, F_, k_, dt):
    def step(u, v):
        lap_u = masked_laplacian(u, domain_f)
        lap_v = masked_laplacian(v, domain_f)
        uvv = u * v * v
        u = u + dt * (Du * lap_u - uvv + F_ * (1.0 - u))
        v = v + dt * (Dv * lap_v + uvv - (F_ + k_) * v)
        u = torch.where(domain, u.clamp(0, 1), torch.zeros_like(u))
        v = torch.where(domain, v.clamp(0, 1), torch.zeros_like(v))
        return u, v
    return step


def make_new_step(domain, kernel, correction, Du, Dv, F_, k_, dt):
    def step(u, v):
        lap_u = masked_laplacian_conv3d(u, kernel, correction)
        lap_v = masked_laplacian_conv3d(v, kernel, correction)
        uvv = u * v * v
        u = u + dt * (Du * lap_u - uvv + F_ * (1.0 - u))
        v = v + dt * (Dv * lap_v + uvv - (F_ + k_) * v)
        u = torch.where(domain, u.clamp(0, 1), torch.zeros_like(u))
        v = torch.where(domain, v.clamp(0, 1), torch.zeros_like(v))
        return u, v
    return step


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", type=int, default=192)
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--warmup", type=int, default=20)
    p.add_argument("--F", type=float, default=0.042)
    p.add_argument("--k", type=float, default=0.062)
    p.add_argument("--Du", type=float, default=0.16)
    p.add_argument("--Dv", type=float, default=0.08)
    p.add_argument("--dt", type=float, default=0.18)
    p.add_argument("--topology", type=str, default="central")
    p.add_argument("--seed", type=int, default=1000)
    p.add_argument("--compile", action="store_true",
                   help="also time torch.compile'd conv3d step -- only "
                        "worth trying if plain conv3d speedup is < 3x")
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        print("[bench] WARNING: no CUDA device -- this number is a "
              "correctness/sanity check only, NOT the deliverable T4 "
              "speedup figure.")

    domain, inner, border, r, R = build_masks(args.grid, device)
    domain_f = domain.float()
    rng = np.random.default_rng(args.seed)
    u0, v0, _, _ = seed_fields_v2(args.grid, args.topology, rng, domain, r, R,
                                  device, shell_thickness=3.0)

    kernel, _ = build_laplacian_kernel(device, domain_f.dtype)
    correction = build_boundary_correction(domain_f)

    old_step = make_old_step(domain, domain_f, args.Du, args.Dv, args.F, args.k, args.dt)
    new_step = make_new_step(domain, kernel, correction, args.Du, args.Dv, args.F, args.k, args.dt)

    print(f"[bench] device={device} grid={args.grid}^3 steps={args.steps} "
          f"warmup={args.warmup}")

    t_old, _, _ = time_loop(old_step, u0.clone(), v0.clone(), args.steps, args.warmup, device)
    print(f"[bench] old (roll-based):  {t_old:8.2f} s  "
          f"({1000*t_old/args.steps:.2f} ms/step)")

    t_new, _, _ = time_loop(new_step, u0.clone(), v0.clone(), args.steps, args.warmup, device)
    print(f"[bench] new (conv3d):      {t_new:8.2f} s  "
          f"({1000*t_new/args.steps:.2f} ms/step)")

    speedup = t_old / t_new if t_new > 0 else float("inf")
    print(f"[bench] speedup: {speedup:.2f}x  "
          f"({'>= 3x, criterion met' if speedup >= 3.0 else '< 3x'})")

    if args.compile:
        compiled_step = torch.compile(new_step)
        t_c, _, _ = time_loop(compiled_step, u0.clone(), v0.clone(), args.steps, args.warmup, device)
        print(f"[bench] new+compile:       {t_c:8.2f} s  "
              f"({1000*t_c/args.steps:.2f} ms/step)")
        speedup_c = t_old / t_c if t_c > 0 else float("inf")
        print(f"[bench] speedup w/ compile: {speedup_c:.2f}x")
    elif speedup < 3.0:
        print("[bench] speedup below 3x -- rerun with --compile to check "
              "whether torch.compile clears the bar before considering "
              "any further optimization.")


if __name__ == "__main__":
    main()
