#!/usr/bin/env python3
"""
SCOPE topology experiment
=========================
Test: does the SPATIAL TOPOLOGY of the initial complexity seed
(central / shell / distributed) predict the TEMPORAL STATISTICS of
boundary export kappa(t) in a spherical Gray-Scott system?

Design decisions (addressing the review of the SCOPE paper):
  1. K is DEFINED explicitly: gzip-compressed bytes per voxel of the
     8-bit-quantized v field in a region (a computable stand-in for
     Kolmogorov complexity; cf. Cilibrasi & Vitanyi 2005).
     kappa(t) = K_border(t) / K_inner(t).
  2. ENSEMBLE runs per topology (--n-runs) -> mean +/- std, not a
     single trajectory.
  3. DOMAIN-SIZE control (--scale) to separate genuine export from
     trivial homogenization: if kappa(t) collapses onto the same curve
     in pattern time regardless of R, the kappa->1 approach is
     equilibration, not export.
  4. First-passage time tau = first t with kappa(t) >= --parity.

Usage (GPU box, e.g. vast.ai):
  pip install torch numpy matplotlib
  python scope_topology.py --grid 96 --steps 20000 --n-runs 8
  python scope_topology.py --grid 192 --steps 20000 --n-runs 8 --scale 2 \
      --outdir results_x2   # domain-size control

Small CPU smoke test:
  python scope_topology.py --grid 32 --steps 800 --n-runs 2 --record-every 100
"""

import argparse
import gzip
import json
import os
import time

import numpy as np
import torch


# ----------------------------------------------------------------------
# Complexity proxy
# ----------------------------------------------------------------------
def K_compress(field_np: np.ndarray) -> float:
    """Compressed bytes per voxel of the 8-bit quantized field.

    This is the operational complexity proxy. Uniform regions compress
    to ~0; structured (pattern-bearing) regions compress poorly.
    """
    if field_np.size == 0:
        return 0.0
    lo, hi = field_np.min(), field_np.max()
    if hi - lo < 1e-12:
        q = np.zeros(field_np.shape, dtype=np.uint8)
    else:
        q = ((field_np - lo) / (hi - lo) * 255).astype(np.uint8)
    raw = q.tobytes()
    comp = gzip.compress(raw, compresslevel=6)
    return len(comp) / field_np.size


# ----------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------
def build_masks(n: int, device):
    """Spherical domain of radius R=0.46*n inside an n^3 grid.

    Regions:
      inner  : r <= 0.50 R
      border : 0.85 R <= r <= R   (outer shell, ~boundary layer)
    """
    ax = torch.arange(n, dtype=torch.float32, device=device) - (n - 1) / 2
    X, Y, Z = torch.meshgrid(ax, ax, ax, indexing="ij")
    r = torch.sqrt(X**2 + Y**2 + Z**2)
    R = 0.46 * n
    domain = r <= R
    inner = r <= 0.50 * R
    border = (r >= 0.85 * R) & (r <= R)
    return domain, inner, border, r, R


def seed_fields(n, topology, rng, domain, r, R, device):
    """u=1, v=0 background; seed blobs of (u=0.5, v=0.25).

    Total seeded volume is matched across topologies (~0.7% of domain)
    so only the SPATIAL ARRANGEMENT differs.
    """
    u = torch.ones((n, n, n), device=device)
    v = torch.zeros((n, n, n), device=device)
    target = 0.007 * domain.sum().item()

    if topology == "central":
        # one ball at the center
        rad = (target * 3 / (4 * np.pi)) ** (1 / 3)
        mask = r <= rad
    elif topology == "shell":
        # thin spherical shell at 0.75 R
        r0 = 0.75 * R
        th = 0.5
        while True:
            mask = (r >= r0 - th) & (r <= r0 + th) & domain
            if mask.sum().item() >= target:
                break
            th += 0.25
    elif topology == "distributed":
        # many small balls at random positions inside 0.9 R
        mask = torch.zeros_like(domain)
        blob_r = max(2.0, 0.03 * n)
        blob_vol = 4 / 3 * np.pi * blob_r**3
        n_blobs = max(4, int(target / blob_vol))
        ax = torch.arange(n, dtype=torch.float32, device=device) - (n - 1) / 2
        X, Y, Z = torch.meshgrid(ax, ax, ax, indexing="ij")
        placed = 0
        while placed < n_blobs:
            c = (torch.tensor(rng.uniform(-1, 1, 3), device=device) * 0.9 * R)
            if c.norm() > 0.9 * R:
                continue
            d = torch.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
            mask |= d <= blob_r
            placed += 1
    else:
        raise ValueError(topology)

    mask &= domain
    u[mask] = 0.5
    v[mask] = 0.25
    # small noise inside seeds only (reproducible via rng)
    noise = torch.tensor(
        rng.uniform(-0.02, 0.02, size=(n, n, n)), dtype=torch.float32, device=device
    )
    v = torch.where(mask, v + noise, v)
    u = torch.where(domain, u, torch.zeros_like(u))
    v = torch.where(domain, v, torch.zeros_like(v))
    return u, v, mask


# ----------------------------------------------------------------------
# Gray-Scott with no-flux (Neumann) BC on an irregular spherical boundary
# ----------------------------------------------------------------------
def masked_laplacian(f, domain_f):
    """6-neighbor Laplacian with no-flux at the domain boundary.

    For each neighbor outside the domain the flux contribution is zero:
    lap = sum_over_valid_neighbors(f_nb - f_center).
    """
    lap = torch.zeros_like(f)
    for dim in (0, 1, 2):
        for shift in (1, -1):
            f_nb = torch.roll(f, shifts=shift, dims=dim)
            m_nb = torch.roll(domain_f, shifts=shift, dims=dim)
            lap = lap + m_nb * (f_nb - f)
    return lap


@torch.no_grad()
def run_one(n, topology, seed, args, device):
    domain, inner, border, r, R = build_masks(n, device)
    domain_f = domain.float()
    rng = np.random.default_rng(seed)
    u, v, _ = seed_fields(n, topology, rng, domain, r, R, device)

    inner_idx = inner.cpu().numpy()
    border_idx = border.cpu().numpy()

    Du, Dv, F, k, dt = args.Du, args.Dv, args.F, args.k, args.dt
    times, kappas, K_in_list, K_bd_list = [], [], [], []

    for step in range(args.steps + 1):
        if step % args.record_every == 0:
            v_np = v.cpu().numpy()
            K_in = K_compress(v_np[inner_idx])
            K_bd = K_compress(v_np[border_idx])
            kappa = K_bd / K_in if K_in > 1e-9 else float("nan")
            times.append(step * dt)
            kappas.append(kappa)
            K_in_list.append(K_in)
            K_bd_list.append(K_bd)

        lap_u = masked_laplacian(u, domain_f)
        lap_v = masked_laplacian(v, domain_f)
        uvv = u * v * v
        u = u + dt * (Du * lap_u - uvv + F * (1.0 - u))
        v = v + dt * (Dv * lap_v + uvv - (F + k) * v)
        u = torch.where(domain, u.clamp(0, 1), torch.zeros_like(u))
        v = torch.where(domain, v.clamp(0, 1), torch.zeros_like(v))

    # first passage over parity
    tau = None
    for t, ka in zip(times, kappas):
        if np.isfinite(ka) and ka >= args.parity:
            tau = t
            break
    return {
        "topology": topology,
        "seed": seed,
        "t": times,
        "kappa": kappas,
        "K_inner": K_in_list,
        "K_border": K_bd_list,
        "tau_first_passage": tau,
    }


# ----------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", type=int, default=96, help="grid size n (n^3)")
    p.add_argument("--steps", type=int, default=20000)
    p.add_argument("--record-every", type=int, default=200)
    p.add_argument("--n-runs", type=int, default=8, help="ensemble size per topology")
    p.add_argument("--F", type=float, default=0.06)
    p.add_argument("--k", type=float, default=0.062)
    p.add_argument("--Du", type=float, default=0.16)
    p.add_argument("--Dv", type=float, default=0.08)
    p.add_argument("--dt", type=float, default=0.18)
    p.add_argument("--parity", type=float, default=1.0, help="kappa threshold for tau")
    p.add_argument("--scale", type=float, default=1.0,
                   help="label for domain-size control runs (metadata only)")
    p.add_argument("--outdir", type=str, default="results")
    p.add_argument("--topologies", nargs="+",
                   default=["central", "shell", "distributed"])
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[scope] device={device}, grid={args.grid}^3, steps={args.steps}, "
          f"runs/topology={args.n_runs}")
    os.makedirs(args.outdir, exist_ok=True)

    all_runs = []
    for topo in args.topologies:
        for i in range(args.n_runs):
            t0 = time.time()
            res = run_one(args.grid, topo, seed=1000 + i, args=args, device=device)
            all_runs.append(res)
            ktail = res["kappa"][-1]
            print(f"[scope] {topo:12s} run {i}: kappa(T)={ktail:.3f} "
                  f"tau={res['tau_first_passage']} ({time.time()-t0:.1f}s)")

    meta = {"args": vars(args), "device": str(device)}
    with open(os.path.join(args.outdir, "runs.json"), "w") as f:
        json.dump({"meta": meta, "runs": all_runs}, f)
    print(f"[scope] wrote {args.outdir}/runs.json")

    # ------------------------------------------------------------------
    # summary + plot
    # ------------------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        colors = {"central": "tab:red", "shell": "tab:blue",
                  "distributed": "tab:green"}
        summary = {}
        for topo in args.topologies:
            runs = [r for r in all_runs if r["topology"] == topo]
            t = np.array(runs[0]["t"])
            K = np.array([r["kappa"] for r in runs])
            mean, std = np.nanmean(K, 0), np.nanstd(K, 0)
            axes[0].plot(t, mean, color=colors.get(topo, None), label=topo)
            axes[0].fill_between(t, mean - std, mean + std, alpha=0.2,
                                 color=colors.get(topo, None))
            taus = [r["tau_first_passage"] for r in runs
                    if r["tau_first_passage"] is not None]
            summary[topo] = {
                "kappa_T_mean": float(np.nanmean(K[:, -1])),
                "kappa_T_std": float(np.nanstd(K[:, -1])),
                "tau_mean": float(np.mean(taus)) if taus else None,
                "tau_std": float(np.std(taus)) if taus else None,
                "n_passed": len(taus), "n_runs": len(runs),
            }
            if taus:
                axes[1].scatter([topo] * len(taus), taus, alpha=0.6,
                                color=colors.get(topo, None))
        axes[0].axhline(args.parity, ls="--", c="gray", lw=1)
        axes[0].set_xlabel("t"); axes[0].set_ylabel(r"$\kappa(t)$")
        axes[0].set_title(r"$\kappa(t)$ mean $\pm$ std per seed topology")
        axes[0].legend()
        axes[1].set_ylabel(r"$\tau$ (first passage)"); axes[1].set_title(
            "First-passage times")
        fig.tight_layout()
        fig.savefig(os.path.join(args.outdir, "kappa_topologies.png"), dpi=150)
        with open(os.path.join(args.outdir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        print(json.dumps(summary, indent=2))
    except ImportError:
        print("[scope] matplotlib not available; skipped plots")


if __name__ == "__main__":
    main()
