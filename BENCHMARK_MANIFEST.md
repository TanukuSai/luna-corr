# LUNA-CORR Benchmark Manifest

This manifest is the canonical scientific authority for all experimental results reported in the LUNA-CORR codebase, documentation, and presentations. Every reported number derives directly from an executable benchmark script and a frozen artifact in `results/`.

---

## Canonical Experiment Summary Table

| Experiment ID | Scientific Purpose | Evaluation Protocol | Dataset & Sensor | Sample Size ($N$) | Primary Metric | Reported Value | Canonical Artifact |
|---|---|---|---|---|---|---|---|
| **`EXP-OHRC-E2E`** | End-to-end cross-orbit repeat registration | 20% random withheld correspondences (frozen split) | Chandrayaan-2 OHRC (`ch2_ohr_ncp_20260716t1429432706` vs `...1627551900`) | $N=165$ held-out ($N=657$ fit, 822 inliers, 99.2% ratio) | Held-out RMSE / Median / P95 | **0.679 px** RMSE (median: 0.506 px, P95: 1.294 px) | [`results/real_ohrc_cross_orbit/result.json`](results/real_ohrc_cross_orbit/result.json) |
| **`EXP-TMC-E2E`** | End-to-end stereo triplet relief registration | 20% random withheld correspondences (frozen split) | Chandrayaan-2 TMC-2 Fore vs Nadir (`ch2_tmc_nra_...` vs `ch2_tmc_nrn_...`) | $N=138$ held-out ($N=548$ fit, 686 inliers, 77.0% ratio) | Held-out RMSE / Median / P95 | **1.110 px** RMSE (fitting: 0.841 px, median: 0.689 px, P95: 2.012 px) | [`results/real_tmc2_stereo_checkpointed/result.json`](results/real_tmc2_stereo_checkpointed/result.json) |
| **`EXP-TMC-FIXED`** | Pipeline stage ablation & non-rigid gain | Fixed $N=150$ held-out set strictly withheld across all stages ($B=1000$ bootstrap) | Chandrayaan-2 TMC-2 Stereo | $N=150$ fixed held-out points | Held-out RMSE [95% CI] | Stage 1 (Raw SIFT): **2.119 px**<br>Stage 3 (RootSIFT): **1.522 px**<br>Stage 5 (TPS): **0.841 px** (**44.7% gain** vs Stage 3) | [`results/ablation_bootstrap_ci.json`](results/ablation_bootstrap_ci.json) |
| **`EXP-NEG-DISJOINT`** | Fail-safe quality control & false-match rejection | Automated rejection threshold ($N < 20$ or spatial entropy $< 0.5$) | Disjoint lunar scenes (Apollo 11 mare vs South Pole crater) | 1 pair (5 candidate inliers retained, 0 accepted) | Acceptance decision | **REJECTED** (Reason: `INSUFFICIENT_INLIERS`, fails safely) | [`results/negative_control_disjoint/result.json`](results/negative_control_disjoint/result.json) |
| **`EXP-SYN-ILLUM`** | Controlled photometric normalization under sun sweep | Known identity geometry + realistic sensor shot noise ($\sigma=0.01$) | NASA LOLA South Pole DEM (`ldac_50s_1000m.jp2`), $\Delta\text{Az} \in [0^\circ, 180^\circ]$ | Sweep of 7 sun angles | Precision@1px & Inlier yield | Direct SIFT: Collapses at $\Delta\theta \ge 45^\circ$ ($N < 20$, 0.0% prec)<br>Mode C: **742–1,187 inliers**, **>99.1% prec @ 1px** | [`results/synthetic_illumination_groundtruth.json`](results/synthetic_illumination_groundtruth.json) |

---

## Detailed Experiment Protocols

### 1. `EXP-OHRC-E2E` (Real Mission OHRC Cross-Orbit)
- **Input Data**: Science-calibrated browse products from ISRO PRADAN archive.
  - Orbit A: `ch2_ohr_ncp_20260716t1429432706_b_brw_d18`
  - Orbit B: `ch2_ohr_ncp_20260716t1627551900_b_brw_d18`
- **GSD**: ~0.25 m nominal.
- **Pipeline Execution**: Full 8-stage pipeline with Local Contrast Normalization (LCN), RootSIFT, MAGSAC++ outlier rejection, and Relief Coherence Gate ($S_{\text{relief}} = 0.498 > 0.20 \implies \text{TPS}$).
- **Outcome**: 822 inliers retained out of 829 candidates (99.2% inlier ratio).
- **Validation**: 20% random partition withheld from transformation fitting ($N = 165$ points). Fitting RMSE = 0.624 px; **Held-out RMSE = 0.679 px**; Held-out median = 0.506 px; Held-out P95 = 1.294 px.
- **Evidence Boundary**: Evaluated against internally withheld correspondences; independent laser altimetry (LOLA) geodetic ground truth is pending.

### 2. `EXP-TMC-E2E` (Real Mission TMC-2 Stereo Triplet)
- **Input Data**: Fore camera (`nra`) vs Nadir camera (`nrn`) acquired on 2026-08-15.
  - Source: `ch2_tmc_nra_20260815t2104543018_b_brw_d18`
  - Reference: `ch2_tmc_nrn_20260815t2104543018_b_brw_d18`
- **GSD**: ~5.0 m nominal.
- **Pipeline Execution**: 8-stage pipeline. Inliers = 686 (77.0% ratio). Relief coherence $S_{\text{relief}} = 0.676 > 0.20$ triggered non-rigid Thin-Plate Spline (TPS) transformation.
- **Validation**: 20% withheld partition ($N = 138$ points). Fitting RMSE = 0.841 px; **Held-out RMSE = 1.110 px**; Held-out median = 0.689 px; Held-out P95 = 2.012 px.

### 3. `EXP-TMC-FIXED` (Fixed Evaluation Set Ablation, $N=150$)
- **Purpose**: Measure the incremental contribution of each algorithmic stage on an identical, strictly isolated set of $N=150$ evaluation points.
- **Protocol**:
  - A fixed evaluation set of $N=150$ points was generated from consensus inliers and frozen (`seed=42`).
  - **Zero Leakage Discipline**: For every stage (Stages 1 through 5), all candidate training points within a $3.0\text{ px}$ Euclidean radius of the $N=150$ test points were strictly excluded prior to model fitting.
  - Non-parametric bootstrap resampling ($B=1000$ iterations) was performed to estimate 95% confidence intervals.
- **Results**:
  - Stage 1 (Raw SIFT): RMSE = 2.119 px [1.829, 2.402]
  - Stage 2 (+ LCN): RMSE = 1.557 px [1.435, 1.667]
  - Stage 3 (+ RootSIFT): RMSE = 1.522 px [1.392, 1.646]
  - Stage 4 (+ Soft Utility Quotas): RMSE = 1.522 px [1.383, 1.644]
  - Stage 5 (+ Adaptive TPS): **0.841 px [0.711, 0.971]**
- **Error Reduction**: **44.7% reduction** in held-out RMSE relative to Stage 3 rigid/projective baseline ($1.522 \to 0.841\text{ px}$); **60.3% reduction** relative to Raw SIFT ($2.119 \to 0.841\text{ px}$).

### 4. `EXP-NEG-DISJOINT` (Disjoint Negative Control)
- **Purpose**: Verify that the pipeline explicitly rejects non-overlapping scenes rather than hallucinating false alignments.
- **Input**: Spatially disjoint scenes from different lunar hemispheres.
- **Result**: Only 5 candidate matches detected ($N < 20$ gating threshold). Status: **REJECTED**, Reason: `INSUFFICIENT_INLIERS`. Fails safely.

### 5. `EXP-SYN-ILLUM` (Controlled Photometric Normalization Benchmark)
- **Input**: NASA LOLA South Pole DEM (`ldac_50s_1000m.jp2`, ~1 km GSD) rendered under varying solar azimuth $\theta_{\text{az}} \in [45^\circ, 225^\circ]$ ($\Delta\theta \in [0^\circ, 180^\circ]$) using the Lommel-Seeliger / Lunar-Lambert physical reflectance model with ray-traced shadows.
- **Noise Injection**: Additive Gaussian sensor shot noise ($\sigma = 0.01$, SNR ~ 40 dB) added to the target image.
- **Direct Optical vs Mode C**:
  - At $\Delta\theta = 0^\circ$: Direct retains 737 inliers (0.257 px RMSE); Mode C retains 737 inliers (0.257 px RMSE).
  - At $\Delta\theta = 45^\circ$: Direct degrades to 28 inliers (0.0% precision @ 1px, 505 px RMSE); Mode C recovers **898 inliers** (99.3% precision @ 1px, 0.252 px RMSE).
  - At $\Delta\theta = 90^\circ$: Direct collapses to 7 inliers (suppressed); Mode C recovers **932 inliers** (99.1% precision @ 1px, 0.200 px RMSE).
  - At $\Delta\theta = 180^\circ$ (opposite sun): Direct collapses to 10 inliers (suppressed); Mode C recovers **742 inliers** (99.1% precision @ 1px, 0.279 px RMSE).
- **Scientific Disclaimer**: Mode C re-illumination reconstructs the reference appearance under the target solar geometry when a baseline DEM is available. This validates the controlled photometric rendering mechanics; it does not substitute for real multi-phase flight validation.
