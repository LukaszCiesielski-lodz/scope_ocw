# Topological control of transport statistics in a spherical Gray-Scott system

## Abstract

We investigate how the spatial topology of initial seeding controls the first-passage statistics of structure transport to the boundary in a three-dimensional Gray-Scott reaction-diffusion system on a spherical domain with no-flux boundary conditions. Three seed topologies of equal volume — central concentration, sub-boundary shell, and space-filling distribution — are systematically compared using pre-registered acceptance criteria and Kaplan-Meier survival analysis of boundary dissipation onset times τ_border.

Across two grid resolutions (192³ and 288³, combined n=28 per topology) we find that the ordering distributed < shell < central is preserved with median τ_border ratios spanning nearly one decade, stable across threshold choices of 1–50% and yielding log-rank p_Holm ≤ 1.3 × 10⁻⁶ for all pairwise contrasts on both scales. Reproducibility was verified by independently seeded batches (n=6+6) run two weeks apart on identical parameters, yielding median τ_border differences below 1% and confirming session-to-session stability. The scale ratio τ(288³)/τ(192³) = 1.40 for shell falls within pre-registered transport bounds [1.25, 1.75], indicating front-propagation scaling. Comparison against a parametric sensitivity yardstick (F,k) ±0.5% in the working regime shows topological effects exceeding parametric noise by factors 3.1× and 4.7× for the two dominant contrasts, and 1.57× for the shell-distributed contrast — the latter at the boundary of methodological acceptability.

Results establish topology of dissipative seeding as a quantitative predictor of temporal transport statistics within Prigogine's dissipative structure framework, complementing existing thermodynamic descriptions of pattern formation.

## II. Model and Methods (draft 1)

### II.A Model and domain

We study the Gray-Scott reaction-diffusion system for two scalar fields u(r,t), v(r,t):

∂_t u = D_u ∇²u − uv² + F(1−u), ∂_t v = D_v ∇²v + uv² − (F+k)v,

with D_u = 0.16, D_v = 0.08, F = 0.042, k = 0.062, integrated by explicit Euler stepping (dt = 0.18) on cubic grids of 192³ and 288³ sites. The working point (F, k) was selected in a pilot phase as the regime in which all three seeding topologies produce persistent, non-saturating patterns; it was frozen before confirmation runs. The computational domain is a sphere inscribed in the cubic grid, with no-flux (Neumann) boundary conditions enforced through a masked-Laplacian formulation. The Laplacian is evaluated as a 3D convolution with a boundary-corrected kernel; numerical equivalence of this implementation against a reference finite-difference version was verified to max|Δ| = 1.79 × 10⁻⁷ (tolerance 10⁻⁶) on the target hardware. Details of the discretization and the equivalence gate are given in Appendix A.

### II.B Seeding topologies

Three initial seeding topologies of equal seeded volume are compared: central (a single ball at the domain center), shell (a spherical layer beneath the boundary), and distributed (randomized non-overlapping balls filling the domain). Seeded-volume matching across topologies is verified per run (match ratio 1.00 ± 0.01). At 192³ the shell thickness is 3.0 voxels, yielding a seeded fraction of ≈5.7% for all topologies. At 288³ two variants are used: a self-similar shell (thickness 4.5, preserving the 5.7% fraction; arm B′) and a fixed-thickness variant (3.0, fraction ≈3.8%; arm C). The resulting confound between domain scale and seeded fraction in arm C is deliberate and is addressed in the interpretation of scale ratios (Sec. IV).

### II.C Observable

The primary observable is τ_border: the first time the boundary dissipation rate — the reaction dissipation integrated over the shell r ∈ [0.85R, R], an operational proxy for the diffusive component of entropy production in the decomposition of Falasco et al. — reaches 10% of its own final value at the horizon T. The per-run adaptive threshold normalizes across topologies with different asymptotic export levels; we note this normalization acts against the transport hypothesis (topologies with low asymptotic export reach their own 10% more easily), making it conservative. Runs never reaching threshold are right-censored at T. Threshold stability is assessed secondarily over the range 1–50%.

### II.D Pre-registered protocol

Evaluation criteria were frozen before confirmation (CRITERIA v2): per-arm validity gates (all runs alive, volume matching, fraction consistency, non-degenerate dissipation), pairwise log-rank (Mantel-Cox) tests on Kaplan-Meier curves with Holm correction, and three disjoint verdicts (CONFIRMED / NEGATIVE / INCONCLUSIVE). Scaling bounds for the 288³/192³ median ratio — [1.25, 1.75] for front-propagation transport, ≤1.15 for homogenization — were pre-registered before arm B′ was run. Confirmation comprised arm A (192³, n = 16 per topology), arm B′ (288³, shell only, n = 12), and arm C (288³, all topologies, n = 12, executed as two independent batches two weeks apart). A parametric sensitivity yardstick — nine runs on a 3×3 grid of (F, k) ± 0.5% at fixed topology and seed — quantifies working-point sensitivity of τ_border for comparison against inter-topology effects. All runs used seeds 2000–2011 on dual NVIDIA T4 GPUs; the complete audit trail (frozen criteria, changelog, raw outputs) is available in the public repository.

### Appendix A (szkielet — do napisania później)

- A.1: Masked-Laplacian discretization; boundary-corrected conv3d kernel; equivalence gate procedure and result
- A.2: Horizon rule (T scaling with grid size per CRITERIA §7: 8100 records at 192³, 12060 at 288³)
- A.3: Seeding construction details (ball packing for distributed; shell geometry; match-ratio computation)
- A.4: Survival analysis details (Kaplan-Meier estimator, log-rank statistic, Holm procedure, censoring handling)

## III. Results (draft 1)

### III.A Primary arm: topology orders transport at 192³

All 48 runs of arm A (n = 16 per topology) passed the validity gates: every run alive at horizon, seeded fractions 5.71–5.74%, fill factors 0.619–0.620 across topologies. Median first-passage times at the 10% threshold were τ_border = 360 (distributed), 1350 (shell), and 3330 (central) — a span of nearly one decade. All pairwise log-rank contrasts are significant after Holm correction (p_Holm ≤ 1.9 × 10⁻⁷; Table I), with no censored runs and non-overlapping confidence intervals. The ordering distributed < shell < central is preserved at every threshold in the 1–50% range (Table II), indicating that the effect is not an artifact of the threshold choice.

### III.B Scale control: pre-registered transport bounds

Arm B′ (288³, shell, self-similar seeding at 5.73% fraction, n = 12) yielded median τ_border = 1890, giving a scale ratio τ(288³)/τ(192³) = 1890/1350 = 1.40 — within the pre-registered front-propagation bounds [1.25, 1.75] and far from the homogenization bound (≤1.15). The ratio remains within transport bounds for thresholds 5–25% (1.62, 1.40, 1.28), exceeding the upper bound only at 1% (2.11) and approaching the homogenization boundary at 50% (1.19), consistent with an early transient dominated by local activation and a late regime approaching quasi-stationarity, with front transport dominating the mid-transient where the primary threshold lies.

### III.C Full control arm: ordering replicates at 288³

Arm C (288³, all topologies, n = 12, fixed shell thickness, seeded fraction 3.81–3.83%) reproduced the complete ordering: τ_border = 810 (distributed), 1890 (shell), 4770 (central), with all pairwise contrasts significant (p_Holm ≤ 1.3 × 10⁻⁶; Table I) and threshold-stable across 1–50%. The two halves of arm C, executed as independent batches two weeks apart with disjoint seeds, produced statistically indistinguishable results (shell median τ_diss = 2745 in both; medians of all topologies within 1%).

Scale ratios relative to arm A are 1.40 (shell) and 1.43 (central) — both within transport bounds — and 2.25 (distributed), exceeding the upper bound. The distributed excess is consistent with the deliberate fraction confound of arm C (Sec. II.B): at 3.8% seeded fraction, the distributed topology, whose transport onset relies on seeds already near the boundary, is the most sensitive to seed dilution. The self-similar arm B′ shows that when the fraction is preserved, the shell ratio is cleanly transport-like; a self-similar variant for all topologies is a natural extension.

### III.D Sensitivity yardstick: topological effect vs working-point noise

The (F, k) ± 0.5% probe (nine points, fixed shell topology and seed, 192³) produced τ_border spread of 630 steps (range 1080–1710, median 1350), with fill factors 0.595–0.643 confirming the probe remains within the working regime. Notably, τ_border varied almost exclusively along k, with negligible dependence on F. A wider ±2% probe left the regime entirely (fill 0.51–0.72, spread 3060) and is reported only as a negative reference in the repository.

Against this yardstick, the inter-topology differences at 192³ are 2970 (central−distributed, 4.7×), 1980 (central−shell, 3.1×), and 990 (shell−distributed, 1.57×). The two dominant contrasts exceed working-point sensitivity by clear margins; the shell-distributed contrast lies at the boundary of methodological acceptability and is flagged as such. We emphasize that all three contrasts remain individually significant under log-rank at both scales; the yardstick comparison addresses a distinct question — whether topology outweighs parameter uncertainty — and receives a correspondingly nuanced answer.

## IV. Discussion (draft 1)

### IV.A Physical interpretation

The observed ordering admits a direct transport interpretation. The distributed topology places seeded structure within and near the boundary shell at t = 0, so boundary dissipation activates as soon as local patterns develop. The central topology requires structure to traverse the full domain radius by front propagation before export begins. The shell topology, seeded close to but not within the export layer, lies between. The scale ratio of 1.40 for the fraction-preserving arm B′ — squarely within the pre-registered transport bounds and far from homogenization — supports front propagation as the dominant mechanism in the mid-transient, where the primary threshold lies. The threshold dependence of the ratio (Sec. III.B) delineates the regime boundaries: local activation at early times, quasi-stationary saturation at late times, and transport-dominated dynamics between them.

In the language of the entropy-production decomposition of Falasco et al., τ_border measures the onset time of the diffusive export channel relative to its own asymptotic level. Our results then state: the spatial topology of initial structure predicts when the export channel of a dissipative system opens, with an effect size spanning an order of magnitude and scaling consistent with front transport. This complements the finding of Serna et al. that distinct morphologies can carry identical relative entropy in stationary states: even where stationary thermodynamics is morphology-blind, the transient kinetics of dissipative export is strongly morphology-dependent.

### IV.B Relation to dissipation-driven organization

The ordering — more spatially distributed configurations export earlier — is qualitatively consistent with the broader program relating structure formation to dissipation enhancement, including England's dissipation-driven adaptation. We stress the limits of this connection: our observable is a transient first-passage time, not a stationary dissipation rate, and our simulations involve no selection or adaptation dynamics. A direct test in this framework would compare long-time entropy production rates across topologies in the quasi-stationary regime — a separate study for which the present pipeline is suited but which we have not performed.

### IV.C Limitations

Four limitations deserve explicit statement. First, the shell-distributed contrast (990 steps) exceeds the parametric sensitivity yardstick (630 steps) by only 1.57×; while log-rank significance is unambiguous at both scales, the claim that topology dominates working-point uncertainty is strong only for the contrasts involving the central topology. Second, arm C confounds domain scale with seeded fraction (5.7% → 3.8%); the fraction-preserving control exists only for the shell topology (arm B′), and the anomalous distributed ratio (2.25) is interpreted, but not isolated, as a fraction effect. Third, the sensitivity yardstick rests on a single seed and single topology; a multi-seed, multi-topology yardstick would sharpen the comparison. Fourth, all results pertain to one working point (F = 0.042, k = 0.062) of one model; the strong k-dependence observed in the probe suggests the transport picture should be re-examined across the Gray-Scott phase diagram before any claim of generality.

### IV.D Outlook

Three extensions follow naturally. A self-similar arm C (fraction-preserving seeding for all topologies) would close the confound of Sec. III.C. A cumulative-flux variant of the observable, τ_flux — first passage of integrated boundary dissipation — can be computed from existing raw data and would test robustness to the observable definition. Finally, replacing the reflecting (no-flux) boundary with an absorbing one would probe whether the topological ordering survives when exported structure is irreversibly removed — a minimal model of asymmetric boundaries in dissipative systems.

## V. Conclusions (draft 1)

In a three-dimensional Gray-Scott system on a spherical domain, the spatial topology of equal-volume initial seeding predicts the first-passage statistics of boundary dissipation onset. The ordering distributed < shell < central spans nearly a decade in median τ_border, replicates across two grid resolutions and independent seed batches, is stable across threshold choices, and scales — where seeding is self-similar — within pre-registered front-propagation bounds. Two of three pairwise contrasts exceed parametric working-point sensitivity by factors of 3–5; the third lies at the acceptability boundary and is reported as such. Within Prigogine's framework, these results identify seed topology as a quantitative control parameter for the transient opening of a dissipative system's export channel.

## Acknowledgments (draft 1)

The author thanks the Kaggle platform for computational resources (dual NVIDIA T4 GPUs). This work was developed with substantial editorial, analytical, and software-engineering assistance from Anthropic's Claude (models Sonnet 4.6 and Opus 4.7), used for code review, statistical methodology discussions, literature triage, and manuscript structuring. All scientific decisions — hypothesis, frozen criteria, working-point ratification, verdict interpretation — are the author's own, as documented in the public audit trail.

## Status

Full main text draft 1 completed 2026-08-19 (Abstract, I–V, Acknowledgments, ~2400 words). Pending: Tables I–II (transcription from scope_analyze output), bibliography, Figure 1 (Kaplan-Meier curves + threshold-stability panel), Appendix A full text, LaTeX assembly (revtex4-2). Repo to be made public before arXiv submission.
