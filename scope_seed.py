#!/usr/bin/env python3
"""
Corrected seeding for the topology experiment
=============================================
The original `seed_fields` in scope_topology.py claims to match seeded
volume across topologies at 0.7% of the domain. It does not, and cannot:
a shell at 0.75R holding 0.7% of a sphere's volume needs a thickness of
0.18 voxels at 96^3 (see FINDINGS.md). The original loop starts at
half-thickness 0.5 and only grows, so it exits immediately with a
1-voxel shell carrying 5.46x the target volume -- and a 1-voxel shell is
erased by diffusion (diffusion length sqrt(Dv*T) ~ 17 voxels) before the
reaction can amplify it, which is why `shell` extinguished at every (F,k)
tested.

This module inverts the control: the SHELL sets the budget.

  1. Build the shell at 0.75R with a diffusively survivable thickness
     (default 3 voxels) and count its voxels -> N_target.
  2. Match `central` and `distributed` to N_target exactly (binary search
     on ball radius / accumulate blobs until the union reaches N_target).

The seeded fraction is then whatever the geometry forces (3.8% of the
domain at 288^3) and is IDENTICAL across the three topologies, so "only
the spatial arrangement differs" finally holds. The fraction is reported
in the run metadata rather than assumed, because it is resolution
dependent.
"""

import numpy as np
import torch


def build_shell_mask(r, R, domain, thickness):
    """Spherical shell at 0.75R with the given total thickness (voxels)."""
    r0 = 0.75 * R
    half = thickness / 2.0
    return (r >= r0 - half) & (r <= r0 + half) & domain


def build_central_mask(r, domain, n_target, R):
    """Centered ball matched to n_target voxels by bisection on radius."""
    lo, hi = 0.0, float(R)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        cnt = int(((r <= mid) & domain).sum().item())
        if cnt < n_target:
            lo = mid
        else:
            hi = mid
    return (r <= hi) & domain, hi


def build_distributed_mask(n, rng, domain, R, n_target, device, blob_r=None,
                           border_inner_frac=0.85):
    """Random small balls accumulated until the UNION reaches n_target.
    Accumulating the union (rather than summing blob volumes) is what makes
    the match hold in the presence of overlap.

    Blobs are kept ENTIRELY outside the border measurement shell. The
    original placed centers within 0.9R while the border starts at 0.85R,
    so 12.9% of the distributed seed landed inside the very region whose
    "arrival" the experiment measures: diss_border(t=0) was 3.3e-4 for
    distributed against exactly 0 for central and shell. That pre-loads the
    measurement and disqualifies any first-passage comparison against it.
    """
    if blob_r is None:
        blob_r = max(2.0, 0.03 * n)
    max_center = border_inner_frac * float(R) - blob_r
    if max_center <= blob_r:
        raise ValueError(
            f"blob radius {blob_r:.1f} too large to fit inside "
            f"{border_inner_frac}R = {border_inner_frac*float(R):.1f}")
    ax = torch.arange(n, dtype=torch.float32, device=device) - (n - 1) / 2
    X, Y, Z = torch.meshgrid(ax, ax, ax, indexing="ij")
    mask = torch.zeros_like(domain)
    n_blobs = 0
    max_blobs = 100000
    while int(mask.sum().item()) < n_target and n_blobs < max_blobs:
        c = torch.tensor(rng.uniform(-1, 1, 3), device=device,
                         dtype=torch.float32) * max_center
        if float(c.norm()) > max_center:
            continue
        d = torch.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
        mask |= (d <= blob_r) & domain
        n_blobs += 1
    return mask, n_blobs, blob_r


def seed_fields_v2(n, topology, rng, domain, r, R, device,
                   shell_thickness=3.0, noise_amp=0.02):
    """u=1, v=0 background; seed blobs of (u=0.5, v=0.25).

    Returns (u, v, mask, info). `info` records the realized voxel counts so
    the volume match is auditable per run rather than asserted.
    """
    shell = build_shell_mask(r, R, domain, shell_thickness)
    n_target = int(shell.sum().item())
    v_dom = int(domain.sum().item())
    info = {"n_target": n_target, "domain_voxels": v_dom,
            "target_fraction": n_target / v_dom,
            "shell_thickness": shell_thickness}

    if topology == "shell":
        mask = shell
    elif topology == "central":
        mask, rad = build_central_mask(r, domain, n_target, R)
        info["central_radius"] = rad
        info["central_radius_over_R"] = rad / float(R)
    elif topology == "distributed":
        mask, nb, br = build_distributed_mask(n, rng, domain, R, n_target,
                                              device)
        info["n_blobs"] = nb
        info["blob_radius"] = br
    else:
        raise ValueError(topology)

    mask = mask & domain
    info["n_seeded"] = int(mask.sum().item())
    info["seeded_fraction"] = info["n_seeded"] / v_dom
    info["match_ratio"] = info["n_seeded"] / max(n_target, 1)
    # gate B4: the border shell is a MEASUREMENT region; any seed inside it
    # pre-loads the very quantity whose arrival time is the observable
    border = (r >= 0.85 * R) & (r <= R) & domain
    info["seeded_in_border"] = int((mask & border).sum().item())

    # gate B5: the same hazard on the core side. `inner` reaches 0.5R, so a
    # central ball of radius ~0.485R (what an 11.46% fraction forces at 96^3)
    # very nearly IS the measurement region -- the observable would then read
    # the compressibility of the seed itself, and the central arm would start
    # with a different meaning than the other two. Rule: max seed radius
    # <= 0.8 * inner radius = 0.4R, which caps the fraction at f <= 6.4%.
    inner = (r <= 0.50 * R) & domain
    n_inner = int(inner.sum().item())
    info["seeded_in_inner"] = int((mask & inner).sum().item())
    info["inner_occupancy"] = info["seeded_in_inner"] / max(n_inner, 1)
    # exact, topology-agnostic: outermost seeded voxel
    info["max_seed_radius_over_R"] = (
        float(r[mask].max().item()) / float(R) if info["n_seeded"] else 0.0)
    # B5 constrains a COMPACT seed against the inner region. A shell sits at
    # 0.75R and distributed is dispersed by construction, so neither can
    # engulf the core; the binding case is the central ball.
    info["B5_ok"] = bool(topology != "central"
                         or info["max_seed_radius_over_R"] <= 0.40)

    u = torch.ones((n, n, n), device=device)
    v = torch.zeros((n, n, n), device=device)
    u[mask] = 0.5
    v[mask] = 0.25
    noise = torch.tensor(
        rng.uniform(-noise_amp, noise_amp, size=(n, n, n)),
        dtype=torch.float32, device=device)
    v = torch.where(mask, v + noise, v)
    u = torch.where(domain, u, torch.zeros_like(u))
    v = torch.where(domain, v, torch.zeros_like(v))
    return u, v, mask, info
