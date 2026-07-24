#!/usr/bin/env python3
"""
conv3d masked Laplacian
========================
Drop-in replacement for `scope_topology.masked_laplacian`, used by the v2
pipeline (`scope_topology_v2.py`) only. `scope_topology.py` (v1, the audit
reference `scope_run.py` is verified bit-identical against) is NOT touched --
this is a v2 implementation change, not a protocol change.

Why: the roll-based version does, per field per step,
    lap = sum_{dim in (0,1,2)} sum_{shift in (+1,-1)} m_nb * (f_nb - f)
i.e. 6 torch.roll pairs (f and the domain mask) = 12 rolls, ~24 full-size
tensors per step at n=192 -- the profiled bottleneck (1010 s/run on a T4).

Equivalence. Expand the sum:
    lap = sum_nb m_nb*f_nb  -  f * sum_nb m_nb
f is exactly zero outside `domain` (masked at the end of every step and at
seeding), so wherever m_nb=0 the corresponding f_nb is already 0 -- masking
the neighbor read is redundant. That leaves:
    sum_nb m_nb*f_nb == sum_nb f_nb  =  conv3d(f, faces_kernel)
    sum_nb m_nb        =  deg(x)      =  conv3d(domain_f, faces_kernel)
                                          (in-domain face-neighbor count,
                                           6 in the interior, <6 at the
                                           boundary -- this IS the no-flux
                                           Neumann condition: a missing
                                           neighbor contributes zero flux
                                           rather than being treated as an
                                           exterior Dirichlet zero)
so lap = conv3d(f, faces_kernel) - deg*f. Folding the -6 into the kernel
center (as specified) and compensating:
    conv3d(f, kernel[center=-6, faces=+1]) = conv3d(f, faces_kernel) - 6f
    lap = conv3d(f, kernel_center_minus6) + (6 - deg) * f
`boundary_correction = 6 - deg` depends only on `domain`, so it is computed
ONCE per grid and reused every step -- this is the "boundary mask" for
no-flux Neumann referred to alongside the fixed kernel.

Edge padding note: conv3d zero-pads at the tensor's outer face (index 0 /
n-1); torch.roll instead wraps circularly. The two differ only AT those
outermost index-0/n-1 voxels. Since R = 0.46n is strictly less than the
grid half-width 0.5n - 0.5 for every n used here (n > 12.5), `domain` never
reaches index 0 or n-1, so neither implementation's edge behavior is ever
read for an in-domain voxel and the two are exact for the region that
matters. Verified empirically, not just argued: see
`scope_test_laplacian_equivalence.py`.
"""

import torch
import torch.nn.functional as F

_KERNEL_CACHE = {}


def build_laplacian_kernel(device, dtype=torch.float32):
    """3x3x3 kernel: center=-6, six face neighbors=+1, rest 0. Shape
    (1,1,3,3,3) as required by F.conv3d weight."""
    key = (device, dtype)
    if key not in _KERNEL_CACHE:
        k = torch.zeros((1, 1, 3, 3, 3), device=device, dtype=dtype)
        k[0, 0, 1, 1, 1] = -6.0
        for idx in ((0, 1, 1), (2, 1, 1), (1, 0, 1), (1, 2, 1), (1, 1, 0), (1, 1, 2)):
            k[(0, 0) + idx] = 1.0
        faces = k.clone()
        faces[0, 0, 1, 1, 1] = 0.0
        _KERNEL_CACHE[key] = (k, faces)
    return _KERNEL_CACHE[key]


def build_boundary_correction(domain_f):
    """(6 - deg) per voxel, deg = count of in-domain face-neighbors.
    Zero in the bulk (deg=6); computed once per grid, reused every step."""
    n = domain_f.shape[0]
    _, faces = build_laplacian_kernel(domain_f.device, domain_f.dtype)
    deg = F.conv3d(domain_f.view(1, 1, n, n, n), faces, padding=1).view(n, n, n)
    return 6.0 - deg


def masked_laplacian_conv3d(f, kernel, correction):
    """6-neighbor Laplacian with no-flux at the domain boundary, via a fixed
    3x3x3 conv3d kernel plus a precomputed boundary correction. Numerically
    equivalent to `scope_topology.masked_laplacian` for all in-domain
    voxels (see module docstring); NOT bit-identical (different floating
    -point summation order) so tolerance, not exact equality, is the
    acceptance test."""
    n = f.shape[0]
    lap = F.conv3d(f.view(1, 1, n, n, n), kernel, padding=1).view(n, n, n)
    return lap + correction * f
