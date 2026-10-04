# LUNA-CORR

[![Tests](https://img.shields.io/badge/tests-15%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.14-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hackathon](https://img.shields.io/badge/SIH%202026-PS%2026166-teal.svg)]()

> **Physics-informed lunar image correspondence designed for robustness to illumination, viewpoint, scale and cross-sensor differences.**  
> Built for **Smart India Hackathon 2026** (Problem Statement 26166, Space Applications Centre (SAC), ISRO).

---

## Overview

Lunar image correspondence is notoriously vulnerable to four fundamental physical factors:
1. **Brightness Inversion**: Sun azimuth and elevation variations invert slope brightness and displace cast shadows.
2. **Shadow Migration**: Shadow boundaries move non-rigidly across terrain and do not represent physical surface tie-points.
3. **Relief Parallax**: 3D crater topography violates planar homography assumptions under varying orbital viewpoints.
4. **Texture-Poor Mare**: Basaltic maria lack high-frequency visual textures.

`LUNA-CORR` solves these challenges through an end-to-end, 8-stage pipeline combining **Local Contrast Normalization (LCN)**, **RootSIFT + MAGSAC++ robust geometric fitting**, **soft spatial utility quotas**, and an **autocorrelation-gated Thin-Plate Spline (TPS)** elastic deformation layer with explicit reason-coded abstention, supplemented by an **experimental physics-based DEM re-illumination branch (Mode C)**.

---

## Canonical Experimental Evidence

All reported metrics derive from frozen, executable benchmarks documented in [`BENCHMARK_MANIFEST.md`](BENCHMARK_MANIFEST.md):

| Experiment ID | Dataset / Sensor | Protocol | Key Result | Artifact |
|---|---|---|---|---|
| **`EXP-OHRC-E2E`** | Chandrayaan-2 OHRC (~0.25 m GSD) | Cross-orbit repeat pair; 20% random held-out set ($N=165$) | **822 inliers (99.2%)**<br>**0.679 px held-out RMSE** (median: 0.506 px, P95: 1.294 px) | [`results/real_ohrc_cross_orbit/result.json`](results/real_ohrc_cross_orbit/result.json) |
| **`EXP-TMC-E2E`** | Chandrayaan-2 TMC-2 (~5 m GSD) | Stereo triplet (fore vs nadir); 20% random held-out set ($N=138$) | **686 inliers (77.0%)**<br>**1.110 px held-out RMSE** (fitting: 0.841 px) | [`results/real_tmc2_stereo_checkpointed/result.json`](results/real_tmc2_stereo_checkpointed/result.json) |
| **`EXP-TMC-FIXED`** | Chandrayaan-2 TMC-2 Stereo | Frozen $N=150$ evaluation set; zero-leakage 3 px spatial exclusion ($B=1000$ bootstrap) | Stage 1 (Raw SIFT): 2.119 px<br>Stage 3 (RootSIFT): 1.606 px<br>Stage 5 (Adaptive TPS): **0.836 px [0.718, 0.973]** (**47.9% gain**) | [`results/ablation_bootstrap_ci.json`](results/ablation_bootstrap_ci.json) |
| **`EXP-NEG-DISJOINT`** | Apollo 11 mare vs South Pole | Non-overlapping pair negative control ($N < 20$ gating rule) | **1/1 Rejected** (5 candidate inliers; fails safely) | [`results/negative_control_disjoint/result.json`](results/negative_control_disjoint/result.json) |
| **`EXP-SYN-ILLUM`** | LOLA South Pole DEM (~1 km GSD) | Sun azimuth sweep $0^\circ \to 180^\circ$ + sensor noise ($\sigma=0.01$) | Direct SIFT collapses at $\Delta\theta \ge 45^\circ$ ($N < 20$);<br>Mode C recovers **737–1,187 inliers**, **>99.1% precision @ 1px** | [`results/synthetic_illumination_groundtruth.json`](results/synthetic_illumination_groundtruth.json) |
| **`EXP-IO`** | Chandrayaan-2 OHRC (1.05 GB raster) | 500 random $1024 \times 1024$ window seeks across 93,686 lines | **39.15 ms median** (40.47 ms mean, P95: 55.06 ms) | [`results/seeker_latency.json`](results/seeker_latency.json) |

For comprehensive technical derivations, photogrammetry equations, and failure modes, see [`docs/SCIENTIFIC_REPORT.md`](docs/SCIENTIFIC_REPORT.md).

---

## Architecture

```
[01 Ingest]       -> PDS4 XML label parsing, 16-bit array extraction, SPICE spatial overlap check
[02 Appearance]   -> Local Contrast Normalization (LCN) [Mode C DEM lighting: experimental physics branch]
[03 Match]        -> Tiled coarse-to-fine RootSIFT feature matching
[04 Geometry]     -> MAGSAC++ robust initial projective/homography fit
[05 Spatial QC]   -> Soft-utility spatial quotas (prevents keypoint clustering on single crater rims)
[06 Sub-pixel]    -> Phase-correlation sub-pixel refinement
[07 Relief Gate]  -> Spatial autocorrelation (S_relief > 0.20 AND P95 >= 1.5 px) -> triggers adaptive TPS
[08 Decision]     -> Quality verification & metrics output, or explicit reason-coded ABSTAIN
```

---

## Installation & Setup

### Using pip
```bash
git clone https://github.com/TanukuSai/luna-corr.git
cd luna-corr
pip install -e .
```

### Using Docker
```bash
docker build -t luna-corr:latest .
docker run --rm luna-corr:latest
```

---

## Quickstart & CLI Usage

Run registration on an image pair:
```bash
lunacorr register \
  --source path/to/source.xml \
  --reference path/to/reference.xml \
  --out-dir results/my_run/ \
  --enable-tps
```

Outputs generated in `--out-dir`:
- `result.json`: Structured machine-readable metrics (status, transform matrix, inliers, held-out RMSE, reason codes).
- `registered_image.tif`: Registered raster aligned to the reference coordinate grid.
- `tie_points.csv`: Validated tie points with source/reference pixel coordinates and residuals.
- `checkerboard_overlay.png`: Visual diagnostic checkerboard overlay for operator verification.

---

## Running Benchmarks & Tests

Run the unit test suite:
```bash
python -m pytest tests/
```

Reproduce canonical benchmarks:
```bash
# Fixed N=150 ablation benchmark with non-parametric bootstrap CI (B=1000)
python benchmark_bootstrap_ci.py

# Controlled photometric normalization benchmark across sun-angle sweep
python benchmark_synthetic_illumination_groundtruth.py

# Seeker I/O latency benchmark
python benchmark_seeker_latency.py
```

---

## Scientific Boundaries (What We Do Not Claim)

1. **Independent Geodetic Ground Truth**: The sub-pixel held-out RMSE figures represent withheld correspondence sets; independent geodetic validation against LOLA laser tracks is pending.
2. **Real Multimodal Registration**: Direct optical (OHRC/TMC-2) to hyperspectral (IIRS) cross-modal registration has not been demonstrated on flight data.
3. **Controlled Simulation vs Flight Data**: Mode C re-illumination validates renderer photometric consistency under known geometry; it does not substitute for real multi-phase flight validation.

---

## Repository Structure

```
luna-corr/
├── BENCHMARK_MANIFEST.md        <- Canonical experiment registry and metrics
├── Dockerfile                   <- Container definition
├── pyproject.toml               <- Python package configuration
├── requirements.txt             <- Core dependency specification
├── README.md                    <- Project documentation
├── LUNA-CORR_SIH2026_Presentation.pptx <- SIH 2026 Presentation
├── lunacorr/                    <- Core Python package
│   ├── data/                    <- PDS4 readers and SPICE parsers
│   ├── represent/               <- LCN and photometric preprocessors
│   ├── matchers/                <- Feature detection and matching
│   ├── estimate/                <- Robust MAGSAC and TPS estimators
│   ├── selection/               <- Soft spatial utility selector
│   └── geometry/                <- DEM reflectance renderers (Lommel-Seeliger)
├── tests/                       <- Automated pytest suite
├── docs/
│   └── SCIENTIFIC_REPORT.md     <- Comprehensive scientific and technical report
└── results/                     <- Frozen benchmark artifacts and result.json files
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
