#!/usr/bin/env python3
"""
Thermodynamic-cost observables for SCOPE
========================================
Motivation. The gzip proxy K = len(gzip(v))/n measures DESCRIPTION LENGTH
of a configuration and is blind to what it costs to maintain that
configuration. That blindness is the common mechanism behind both
artifacts documented in FINDINGS.md: a dead field and a saturated field
both score kappa ~ 1, because neither is being charged for anything.

Gray-Scott is a driven dissipative system -- F(1-u) feeds, (F+k)v drains,
and structure persists only under continuous throughput. These observables
read that throughput directly.

Definitions (all densities, so they are grid-size intensive):

  dissipation   D(x) = Du|grad u|^2 + Dv|grad v|^2
      cost of holding gradients. EXACTLY ZERO for a uniform field --
      no header floor, no size dependence. This is the key property:
      it makes "dead" and "saturated" distinguishable, which kappa_gzip
      cannot do.

  reaction      R(x) = u v^2
      autocatalytic throughput U+2V -> 3V; the pattern's metabolic rate.

  feed          W(x) = F(1-u)
      pumping work done on the region by the reservoir.

Gradients are masked: an edge contributes only when BOTH endpoints lie in
the domain, so the irregular spherical boundary (where fields are zeroed)
does not manufacture spurious gradients. Forward differences only, so each
edge is counted once.

CAVEAT, to keep the registers separate as required by CLAUDE.md §7:
Gray-Scott is a phenomenological reaction-diffusion model, not a
thermodynamically consistent one. |grad|^2 is a dissipation ANALOGUE, not
literal entropy production. It is reported as a model observable, not as
a physical entropy. Its justification here is operational: it is a cost
measure with a true zero, which is precisely what the gzip proxy lacks.
"""

import numpy as np
import torch


def masked_grad2(f, domain_f):
    """Sum of squared forward differences over in-domain edges.

    Each edge is counted once and attributed to its lower-index voxel.
    An edge counts only if both endpoints are inside the domain.
    """
    g2 = torch.zeros_like(f)
    for dim in (0, 1, 2):
        m_fwd = torch.roll(domain_f, shifts=-1, dims=dim)
        f_fwd = torch.roll(f, shifts=-1, dims=dim)
        valid = domain_f * m_fwd
        g2 = g2 + valid * (f_fwd - f) ** 2
    return g2


def thermo_fields(u, v, domain_f, Du, Dv, F):
    """Per-voxel dissipation, reaction throughput and feed work."""
    dissipation = Du * masked_grad2(u, domain_f) + Dv * masked_grad2(v, domain_f)
    reaction = u * v * v
    feed = F * (1.0 - u) * domain_f
    return dissipation, reaction, feed


# Ratios are reported only where BOTH regions carry cost above this floor.
#
# Not an arbitrary epsilon. Measured trajectories separate into two regimes
# with twelve orders of magnitude between them: exponentially decaying float
# noise in a region that has no structure (observed: 0, 2.9e-39, 2.2e-33,
# 2.3e-16) and genuine dissipation once structure arrives (observed: 7.6e-4,
# 1.6e-3). 1e-8 sits in that gap, eight orders above the noise and four below
# the physics.
#
# The earlier guard of 1e-14 sat on the edge of the noise band instead, and
# produced a ratio of 1.5e10 plus a spurious first passage at t=1980 the
# moment a physically-zero denominator drifted across it -- the same failure
# mode as the gzip channel's tau=36 artifact (FINDINGS.md).
DISS_FLOOR = 1e-8


def region_mean(field, region_mask):
    """Mean density over a region (0.0 if the region is empty)."""
    n = region_mask.sum()
    if n == 0:
        return 0.0
    return float((field * region_mask).sum().item() / n.item())


def thermo_observables(u, v, domain_f, inner_m, border_m, Du, Dv, F):
    """Region-averaged cost densities plus their border/inner ratios.

    Returns a flat dict. The `*_ratio` entries are the thermodynamic
    analogues of kappa: unlike kappa_gzip they are undefined-by-zero
    rather than pinned to a floor when the field is dead, so a dead run
    is visibly dead instead of scoring a spurious ~1.
    """
    diss, reac, feed = thermo_fields(u, v, domain_f, Du, Dv, F)
    out = {}
    for name, fld in (("diss", diss), ("reac", reac), ("feed", feed)):
        ci = region_mean(fld, inner_m)
        cb = region_mean(fld, border_m)
        out[f"{name}_inner"] = ci
        out[f"{name}_border"] = cb
        # nan, not a number, while the core carries no cost: a ratio against
        # a physically-empty denominator is undefined, not large
        out[f"{name}_ratio"] = (cb / ci) if ci > DISS_FLOOR else float("nan")
    # total (extensive) dissipation, for budget-style bookkeeping
    out["diss_total"] = float(diss.sum().item())
    out["reac_total"] = float(reac.sum().item())
    out["v_mass"] = float((v * domain_f).sum().item())
    return out


def K_floor_bytes(n_voxels: int) -> float:
    """gzip cost per voxel of a uniform region -- the artifact baseline.

    Subtracting this from K_compress gives the floor-corrected complexity
    K_exc, which is what kappa should have been built on if one insists
    on a compression proxy at all.
    """
    import gzip
    if n_voxels == 0:
        return 0.0
    raw = np.zeros(n_voxels, dtype=np.uint8).tobytes()
    return len(gzip.compress(raw, compresslevel=6)) / n_voxels
