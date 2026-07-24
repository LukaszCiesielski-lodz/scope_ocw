#!/usr/bin/env python3
"""
Equivalence gate for the conv3d Laplacian (see scope_laplacian.py docstring
for the derivation). Runs the SAME Gray-Scott integration twice from the
same seeded fields -- once with the old roll-based `masked_laplacian`
(scope_topology.py, v1 reference, untouched), once with the new
`masked_laplacian_conv3d` (scope_laplacian.py) -- and tracks the worst
elementwise |delta| on u and v over the whole trajectory, not just at T.

Acceptance (set before running, per CLAUDE.md/CHANGELOG instructions for
this change): max|delta_u| < TOL and max|delta_v| < TOL over the full
smoke run. FAIL means the conv3d swap does not get merged into
scope_topology_v2.py -- this script's exit code is the gate.

Usage:
  python scope_test_laplacian_equivalence.py                     # 32^3/400, tol 1e-6
  python scope_test_laplacian_equivalence.py --grid 96 --steps 2000
"""

import argparse
import sys

import numpy as np
import torch

from scope_topology import build_masks, masked_laplacian
from scope_seed import seed_fields_v2
from scope_laplacian import (build_laplacian_kernel, build_boundary_correction,
                             masked_laplacian_conv3d)


def run_pair(n, topology, seed, F_, k_, Du, Dv, dt, steps, device):
    domain, inner, border, r, R = build_masks(n, device)
    domain_f = domain.float()
    rng = np.random.default_rng(seed)
    u0, v0, _, _ = seed_fields_v2(n, topology, rng, domain, r, R, device,
                                  shell_thickness=3.0)

    kernel, faces = build_laplacian_kernel(device, domain_f.dtype)
    correction = build_boundary_correction(domain_f)

    u_old, v_old = u0.clone(), v0.clone()
    u_new, v_new = u0.clone(), v0.clone()

    max_du = 0.0
    max_dv = 0.0

    with torch.no_grad():
        for step in range(steps + 1):
            max_du = max(max_du, float((u_old - u_new).abs().max()))
            max_dv = max(max_dv, float((v_old - v_new).abs().max()))

            lap_u_old = masked_laplacian(u_old, domain_f)
            lap_v_old = masked_laplacian(v_old, domain_f)
            uvv_old = u_old * v_old * v_old
            u_old = u_old + dt * (Du * lap_u_old - uvv_old + F_ * (1.0 - u_old))
            v_old = v_old + dt * (Dv * lap_v_old + uvv_old - (F_ + k_) * v_old)
            u_old = torch.where(domain, u_old.clamp(0, 1), torch.zeros_like(u_old))
            v_old = torch.where(domain, v_old.clamp(0, 1), torch.zeros_like(v_old))

            lap_u_new = masked_laplacian_conv3d(u_new, kernel, correction)
            lap_v_new = masked_laplacian_conv3d(v_new, kernel, correction)
            uvv_new = u_new * v_new * v_new
            u_new = u_new + dt * (Du * lap_u_new - uvv_new + F_ * (1.0 - u_new))
            v_new = v_new + dt * (Dv * lap_v_new + uvv_new - (F_ + k_) * v_new)
            u_new = torch.where(domain, u_new.clamp(0, 1), torch.zeros_like(u_new))
            v_new = torch.where(domain, v_new.clamp(0, 1), torch.zeros_like(v_new))

    return max_du, max_dv


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", type=int, default=32)
    p.add_argument("--steps", type=int, default=400)
    p.add_argument("--F", type=float, default=0.042)
    p.add_argument("--k", type=float, default=0.062)
    p.add_argument("--Du", type=float, default=0.16)
    p.add_argument("--Dv", type=float, default=0.08)
    p.add_argument("--dt", type=float, default=0.18)
    p.add_argument("--tol", type=float, default=1e-6)
    p.add_argument("--seed", type=int, default=1000)
    p.add_argument("--topologies", nargs="+",
                   default=["central", "shell", "distributed"])
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[equiv] device={device} grid={args.grid}^3 steps={args.steps} "
          f"F={args.F} k={args.k} tol={args.tol:g}")

    worst_du, worst_dv = 0.0, 0.0
    for topo in args.topologies:
        du, dv = run_pair(args.grid, topo, args.seed, args.F, args.k,
                          args.Du, args.Dv, args.dt, args.steps, device)
        ok = (du < args.tol) and (dv < args.tol)
        print(f"[equiv] {topo:12s} max|du|={du:.3e} max|dv|={dv:.3e} "
              f"{'PASS' if ok else 'FAIL'}")
        worst_du = max(worst_du, du)
        worst_dv = max(worst_dv, dv)

    passed = (worst_du < args.tol) and (worst_dv < args.tol)
    print(f"[equiv] overall max|du|={worst_du:.3e} max|dv|={worst_dv:.3e} "
          f"tol={args.tol:g} -> {'PASS' if passed else 'FAIL'}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
