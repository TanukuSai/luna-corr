# LUNA-CORR: Internal Master Document

**Project:** Multi-modal, Sun-angle and scale invariant image correspondence using Chandrayaan-2 optical images (OHRC, TMC-2, IIRS)
**Problem statement:** SIH 2026, PS 26166, ISRO (Department of Space), Software, Space Technology
**Working project name:** LUNA-CORR (not final)
**Document status:** Design stage. No experiment has been run. Nothing in this document is a measured result.

---

## 0. How to use this document

This is the single internal reference for the team. The slide deck is a six-slide summary of it. If the deck and this document disagree, this document wins, and the deck must be corrected.

### 0.1 Evidence legend

Every technical statement below carries one of these tags.

| Tag | Meaning |
|---|---|
| **[V]** | Verified against a primary or official source during this project's research (ISRO, USGS, NASA, JAXA, a paper page, or software documentation). |
| **[S]** | Stated in the SIH problem statement text. |
| **[H]** | Engineering hypothesis. Reasonable, but must be tested before we rely on it. |
| **[U]** | Unknown. Needs data access or an experiment. |
| **[M]** | Our own definition or design choice. Not an ISRO or published standard. |

### 0.2 Assumptions made when this document and deck were created

1. The deck was built for **PS 26166**. The uploaded reference deck (VAYU-TRACE, PS 26230) was used only for its structure: six slides, a claim-status split, numbered references and speaker notes.
2. **Team ID and registered team name** are unknown to us. The deck shows `[enter portal value]`. The reference deck lists a different team ID and name for a different problem statement, and we did not copy them.
3. **LUNA-CORR** is a working name chosen for the deck. Rename freely.
4. No SIH 2026 calendar dates are used anywhere. Timelines are relative (weeks from start).
5. The deck states the project is at design stage. If the team has already run experiments, update slide 4 and section 12.

### 0.3 Rules the team works under

These rules came out of the red-team discussion and are binding.

1. No performance claim without a reproducible experiment.
2. No sub-pixel claim without coordinate-level ground truth.
3. No "AI is better" claim without a non-AI baseline on the same data and metric.
4. No tuning on the final held-out test set.
5. No cross-modal claim (especially IIRS) without a cross-modal test.
6. No generalization claim from one lunar region.
7. No fabricated numbers, and no published paper's numbers presented as our target.
8. No claim of ISRO endorsement or approval.
9. Synthetic-data results are never presented as real-world validation.
10. The system must be able to abstain.

---

## 1. The problem statement

### 1.1 What ISRO asks for [S]

**Background.** Image registration aligns two or more images of the same scene, taken at different times, viewpoints or by different sensors, into a common coordinate system. The **source (moving)** image is transformed to align with the **reference (fixed)** image.

**Process.** Find match points between source and reference, then align the source to the reference.

**Key challenges named by ISRO.**
- **Illumination variation:** changes in Sun azimuth and elevation change surface appearance and are hard to correlate.
- **Viewpoint variation:** geometric distortion from different camera positions and orientations (shift, scale, rotation, perspective).
- **Scale variation:** missions image from different altitudes and at different spatial resolutions, creating scale ratios.

**Expected solution.** A generic software solution that finds correspondence between Chandrayaan-2 optical images and lunar reference images **with sub-pixel accuracy of the source image, maintaining uniform distribution across the images.**

**Deliverables.**
- Software and a registered product with corresponding match points.
- An evaluation metric (examples given: RMSE, inlier match count, inlier ratio).

**Datasets named.** Chandrayaan-2 OHRC, TMC-2, IIRS images. Reference: LRO NAC images and SELENE images. The "specific datasets link" is listed as **TBD**.

**Mentors listed in the problem statement.** Sri Rohit Mishra, Sri Abdullah Suhail Ayyub Zinjani, Sri K Suresh (all SAC, ISRO). Contact only through official SIH channels unless the organizers say otherwise.

### 1.2 Requirement matrix

| ID | Requirement | Source | Priority | Acceptance evidence we will produce |
|---|---|---|---|---|
| R1 | Find correspondences between a Chandrayaan-2 image and a lunar reference image | [S] | MUST | match_points.csv for each pair |
| R2 | Robust to illumination (Sun azimuth/elevation) variation | [S] | MUST | Results binned by Sun-angle difference |
| R3 | Robust to viewpoint variation | [S] | MUST | Results binned by viewing-geometry difference |
| R4 | Robust to scale variation across sensors and altitudes | [S] | MUST | Results binned by GSD ratio |
| R5 | Sub-pixel accuracy | [S] | MUST | Error against independent check points, with distribution |
| R6 | Uniform distribution of match points across the image | [S] | MUST | Coverage score (our metric) and match maps |
| R7 | Registered product | [S] | MUST | registered_image.tif |
| R8 | Evaluation metrics (RMSE, inlier count, inlier ratio, "etc.") | [S] | MUST | result.json per pair, summary tables |
| R9 | Generic: works for OHRC, TMC-2 and IIRS sources | [S] | MUST (tiered) | Pair ladder results, including honest failures |
| R10 | Reference sources: LRO NAC, SELENE | [S] | MUST | Reference adapters |
| R11 | Software deliverable (runnable) | [S] | MUST | Repo, container, README, demo |
| R12 | Abstain when evidence is weak | [M] | SHOULD | Abstain rate reported |
| R13 | Uncertainty per match | [M] | SHOULD | Confidence/uncertainty columns |
| R14 | Use mission geometry (SPICE) and DEM when available | [H] | SHOULD | Mode A vs B vs C comparison |
| R15 | Interactive UI | [M] | COULD | Demo screens |
| R16 | Official SIH evaluation dataset support | [S] | UNKNOWN | Dataset is TBD; adapter layer designed to accept it |

### 1.3 What the problem statement does not say [U]

- No numeric threshold for "sub-pixel." We do **not** invent one. We report measured error distributions and let the reader judge.
- No definition of "uniform distribution." Our coverage metric (section 7.7) is our own.
- No definition of how the "registered product" is evaluated, or whether ISRO holds its own ground truth.
- No statement of which sensor pairs will be tested. We assume any source against any available reference.
- No compute limits, runtime limit, or platform requirement.

**Action:** ask the SIH helpdesk or mentors (through the official channel) about the five items above. Record answers in section 15.

---

## 2. Sensors, data and tooling

### 2.1 Sensor summary

| Sensor | Type | Spatial resolution | Other characteristics | Status |
|---|---|---|---|---|
| OHRC | Panchromatic camera | ~0.25 m GSD at 100 km per the PRADAN page; ~0.28 m in another ISRO source | ~3 km swath at nadir | [V] with a source discrepancy (see 2.2) |
| TMC-2 | Panchromatic stereo camera | ~5 m | ~0.4-0.85 µm; fore, nadir and aft views; DEM and orthoimage products | [V] |
| IIRS | Imaging infrared spectrometer | ~80 m GSD | ~0.8-5.0 µm; ~256 contiguous bands; ~20 km swath at nadir from 100 km | [V] |
| LRO NAC | Reference optical camera | Typically sub-metre to ~1.5 m per pixel depending on altitude | Large public archive; not Chandrayaan-2 | [V] (one source states 0.5-1.5 m per pixel for south-pole images) |
| SELENE (Kaguya) | Reference imagery/topography | Depends on product | Named by ISRO as reference | [U] products to be chosen |

**Resolution ratios (approximate, from the figures above):** OHRC to TMC-2 is about 20 times; TMC-2 to IIRS is about 16 times; OHRC to IIRS is about 300 times. [H] computed from the stated GSDs; not a published figure.

### 2.2 The OHRC resolution discrepancy

Two ISRO-related sources give slightly different nominal OHRC resolutions (0.25 m and 0.28 m). Pixel size depends on altitude and product. **Rule:** never hard-code a GSD. Read it from each product's label, and record both the nominal and label values in the data audit.

### 2.3 Access, format and licensing

- **Archive:** ISRO Science Data Archive (PRADAN / ISSDC) holds OHRC, TMC-2 and IIRS products. [V]
- **Format:** Public Chandrayaan-2 data are distributed in the **PDS4** standard, with XML labels. Products contain data, geometry and browse components. OHRC and IIRS have raw and calibrated products; TMC-2 also has derived DEM and orthoimage products. [V]
- **Terms:** The PRADAN disclaimer states data sharing is open and free for **non-profit scientific use**, ISRO retains ownership, and commercial use needs permission. [V] Consequence: our repository must **not** redistribute raw mission data. Scripts download from PRADAN, and users accept the terms themselves.
- **Historical archive counts:** A 2021 ISRO release snapshot listed 133 TMC-2, 29 OHRC and 5 IIRS datasets. These are historical counts, **not** the current number of usable products. [V] as history, [U] as present count. We never quote a pair count until we have queried the archive ourselves.
- **SIH dataset:** The problem statement lists the dataset link as TBD. We design an adapter layer so that when it is released we only write a new adapter. [U]

### 2.4 Open tooling that already reads Chandrayaan-2 data [V]

- **USGS ISIS:** can import calibrated Chandrayaan-2 TMC-2 and OHRC PDS4 images with `isisimport`. The templates are autodetected in **ISIS 10.0 and above**. At the time we read the documentation, ISIS 10 was described as a release candidate. **Check the current ISIS release before you plan around it.**
- **SPICE kernels** for Chandrayaan-2 are distributed through the ISIS data area (downloaded with `downloadIsisData chandrayaan2 $ISISDATA`).
- **OHRC workflow (per USGS):** `isisimport`, then `spiceinit`, then `isd_generate -k`. **TMC-2 workflow:** `isd_generate -s` reading kernels from the local data area. Large Chandrayaan-2 images are best written as GeoTIFF rather than ISIS cubes.
- **NASA Ames Stereo Pipeline (ASP)** has a Chandrayaan-2 example using OHRC and TMC-2. It states that the OHRC images had **notable pointing error, so bundle adjustment was needed**, and shows an example stereo pair with a convergence angle of about 25 degrees. It also notes that the **illumination in the TMC-2 ortho image is very different** from the OHRC images, which is exactly our problem. ISIS 10 is required for correct OHRC line-exposure handling.

### 2.5 Data audit checklist (Phase 1, first work item)

For each downloaded product, record in a table:

1. Product ID, instrument, processing level (raw, calibrated, derived).
2. Image width, height, bit depth, radiometric units, no-data value.
3. GSD from the label; nominal versus label value.
4. Acquisition time, Sun azimuth and elevation, incidence, emission and phase angles (from the label or computed from SPICE).
5. Sub-spacecraft position, altitude, viewing geometry.
6. Footprint polygon in lunar coordinates; overlap with candidate references.
7. Whether geometry files and a DEM or orthoimage exist.
8. File size and expected memory footprint.
9. Visual QA: stripes, saturation, shadow fraction, texture level.
10. Whether the product can be imported by ISIS 10 (pass or fail with the error).

**Output of the audit:** a pair inventory (source, reference, overlap area, Sun-angle difference, GSD ratio, viewing-angle difference). This inventory defines the benchmark. We never claim counts before it exists.

---

## 3. The physics of the problem

### 3.1 Why lunar images are hard to match

The Moon has no atmosphere to scatter light. Shadows are sharp and long when the Sun is low, and shade can vanish when the Sun is high. The same terrain therefore changes appearance with Sun geometry.

- **Brightness inversion:** a slope facing the Sun is bright in one image and a slope facing away is dark; at another Sun azimuth the pattern flips.
- **Shadow migration:** the shadow of a rim or boulder moves across the surface, so a "feature" at the shadow edge is not at a fixed ground location.
- **Texture-poor terrain:** smooth mare surfaces offer few distinctive features at certain resolutions.
- **Published evidence [V]:** an ISPRS lunar photogrammetry study reports that conventional matching can fail under large illumination differences and uses photoclinometry-assisted matching to obtain pixel-wise matches. A 2024 ISPRS study renders a LOLA DEM under the same illumination as the NAC image before matching.

**Design consequence:** do not compare raw brightness. Compare structure that survives lighting change, or compare against an image **rendered** under the same lighting.

### 3.2 Viewpoint and 3D relief

A homography exactly describes the mapping between two views of a **plane** (or a pure rotation). Lunar terrain has relief, so different viewpoints produce parallax that varies across the image. [H] widely accepted photogrammetric principle. The ASP example showing pointing error and the use of stereo and bundle adjustment on OHRC supports taking geometry seriously. [V]

**Design consequence:** start with similarity, affine and projective models, but select by evidence, and keep a local or DEM-assisted model as an option. We never assume one global homography is physically exact.

### 3.3 Scale and resolution

Sensors differ by orders of magnitude in GSD. Downsampling a fine image to a coarse grid without low-pass filtering causes aliasing and fake texture. Upsampling a coarse image adds no information.

**Design consequence:** resample to a **common GSD with proper anti-aliasing**, and choose the common GSD deliberately (usually close to the coarser image) rather than by default.

### 3.4 Modality (the IIRS problem)

IIRS is a hyperspectral cube (~256 bands, ~0.8-5 µm, ~80 m). At the longer wavelengths the signal includes thermal emission, so apparent brightness is driven by temperature and composition as well as illumination. [H] The OHRC-to-IIRS gap in resolution (about 300 times) and in physics is the largest in the problem.

**Design consequence:** treat IIRS as its own research track, attempted last. Candidate representations (all [H], to be benchmarked): single reflected-light band, principal components, band ratios, or a learned spectral embedding. We report plainly if it fails.

### 3.5 The ground-truth problem

To compute error we need the "true" location of each point in both images. For real Chandrayaan-2 pairs we usually do not have it. Hence the ground-truth hierarchy in section 8.

---

## 4. Literature and source map

### 4.1 Sources we verified and how each is used

| # | Source | What it shows | How LUNA-CORR uses it | Status |
|---|---|---|---|---|
| 1 | ISRO / ISSDC, Chandrayaan-2 Science Data Archive (PRADAN) | OHRC, TMC-2, IIRS products, PDS4, label structure, usage terms | Data source and sensor specs | [V] |
| 2 | Ames Stereo Pipeline, Chandrayaan-2 example | OHRC pointing error needing bundle adjustment; very different TMC-2 ortho illumination | Justifies bundle adjustment before matching; baseline tooling | [V] |
| 3 | USGS Astrogeology, Chandrayaan 2 page and ISIS ingest guides | PDS4 import, SPICE, ISD generation, GeoTIFF recommendation | Ingestion path | [V] |
| 4 | "An integrated photogrammetric and photoclinometric approach for illumination-invariant pixel-resolution 3D mapping of the lunar surface," ISPRS J. Photogramm. Remote Sens., 2020 | Conventional matching can fail under large lunar illumination differences; photoclinometry-assisted matching | Motivation; illumination-aware representation | [V] (authors and DOI to be added from the publisher page) |
| 5 | Liu P et al., "LOLA DEM Assisted Photogrammetric Processing of LRO NAC Images for the Lunar South Pole," ISPRS Archives XLVIII-1, 2024, 409-416, doi:10.5194/isprs-archives-XLVIII-1-2024-409-2024 | LOLA DEM rendered under the same illumination as NAC images, matched to NAC orthomaps, tie points added to bundle adjustment | Render-and-match design; uniformly distributed control points | [V] |
| 6 | Haase I, Gläser P, Oberst J, "Bundle adjustment of spaceborne double-camera push-broom imagers and its application to LROC NAC imagery," ISPRS Archives XLII-2/W13, 2019, 1397-1404, doi:10.5194/isprs-archives-XLII-2-W13-1397-2019 | Rigorous BA for NAC; LOLA shots as 3D control to register NAC DTM to the global lunar frame | Control-network thinking; check points tied to LOLA | [V] |
| 7 | Li J et al., "RIFT: Multi-modal image matching based on radiation-variation insensitive feature transform," IEEE TIP 29, 2020, 3296-3310, doi:10.1109/TIP.2019.2959244 | Phase-congruency keypoints and descriptors for nonlinear radiometric difference; does not require geographic information | Candidate illumination-robust matcher | [V] |
| 8 | JPL/NASA, Mars 2020 Lander Vision System (project page; NTRS 20230006986 flight performance; Earth and Space Science 2021 reference-map paper) | Descent images projected onto the ground plane and resampled to map orientation and pixel scale; position error under 40 m relative to the map; initial inertial error up to 3.2 km | Geometry-first design precedent | [V] |
| 9a | Sun J et al., LoFTR, CVPR 2021 | Coarse-to-fine transformer matching, strong in low-texture regions | Benchmark candidate | [V] (general-photo benchmarks only) |
| 9b | Lindenberger P et al., LightGlue, ICCV 2023 | Learned sparse matching with adaptive computation | Benchmark candidate | [V] (general-photo benchmarks only) |
| 9c | Edstedt J et al., RoMa, CVPR 2024, 19790-19800 | Dense matcher using frozen DINOv2 features plus fine ConvNet features; 36% gain on WxBS reported by the authors; default input 560 px upsampled to 864 px | Benchmark candidate; forces tiling | [V] |
| 10 | Barath D et al., MAGSAC++, CVPR 2020 | Robust estimator tested on homography and fundamental matrix fitting | Default robust estimator candidate | [V] (not lunar) |
| 11a | Scheffler D et al., AROSICS, Remote Sensing 2017, 9(7), 676 | Phase-correlation sub-pixel co-registration for multi-sensor satellite data; global and local modes | Sub-pixel refinement design; example of local shift fields | [V] |
| 11b | Leprince S et al., COSI-Corr, IEEE 2009 | Orthorectification plus sub-pixel correlation, developed for ground displacement measurement | Sub-pixel refinement precedent | [V] |
| 12 | Tuzcuoğlu Ö et al., XoFTR, CVPR Workshops 2024, 4275-4286 | Cross-modal matching for **thermal infrared and visible** images; pseudo-thermal augmentation; sub-pixel refinement | Idea source for modality-simulating augmentation. **Not** a lunar method | [V] |

### 4.2 Sources mentioned in earlier discussion but **not** re-verified

The earlier research conversation referred to the items below. We did not re-check them in the final verification pass. Do not cite them in the submission until a team member has opened the paper.

- A 2026 paper on a "photometric-weighted invariant feature transform" for planetary image registration, with a multi-illumination LROC NAC benchmark. Earlier notes quote its benchmark numbers. **Do not reuse those numbers.** They belong to their method and benchmark.
- A 2026 Lunar Trailblazer post-acquisition localization paper reporting that SIFT worked well in their setting.
- A multi-illumination LROC NAC crater-neighborhood matching paper (with 8 regions and 4,682 annotated craters, as recalled earlier).
- A paper on a unified transformer for multimodal lunar reconstruction.
- Public GitHub repositories claiming SIH26166 implementations. Their scientific performance is unknown.

**Action item (owner: literature lead):** open each, record title, authors, venue, DOI, data availability and licence, then move to the table above or delete.

### 4.3 Corrections made during verification (keep so we do not repeat them)

1. **RIFT** stands for radiation-variation insensitive feature transform. It is **not** "rotation-invariant." RIFT2 is the rotation-invariant follow-up.
2. **AROSICS** is sub-pixel co-registration based on phase correlation; it is not a "harmonization" tool.
3. **XoFTR** is for thermal-visible matching, not a lunar or general multimodal foundation model.
4. "Orthorectify first" is not enough. The ASP Chandrayaan-2 example shows pointing errors, so the order is SPICE geometry, **then bundle adjustment**, then orthorectification.
5. HOPC and CFOG-style methods need prior geographic information for initialization, which supports orthorectifying first. RIFT does not need it.
6. SIFT is a serious baseline, not a toy. Do not dismiss it.

### 4.4 Prior art at space agencies

| Mission or team | Relevant fact | Status |
|---|---|---|
| NASA/LRO NAC and LOLA | NAC images tied to LOLA in photogrammetric solutions; updated NAC pointing and ephemeris kernels released for polar images, tied to LOLA | [V] |
| NASA Mars 2020 Lander Vision System | Vision-based map-relative localization; descent images resampled to map frame; position error under 40 m relative to the map; landing about 5 m from target per a flight-performance report | [V] |
| JAXA SLIM | Crater-based optical navigation; first pinpoint lunar landing on 19 January 2024; reported about 55 m from target centre | [V] |
| ISRO to JAXA | A secondary report says ISRO provided Chandrayaan-2 images of the SLIM site at different Sun angles | [V] single secondary source; confirm before citing |
| NASA OSIRIS-REx | Stereophotoclinometry (SPC) was a key technology for terrain models and landmark navigation | [V] |
| Rosetta, Dawn | SPC wiki mentions Dawn and code improvements from Rosetta | [V] partial |
| Hayabusa2 and SPC | Not confirmed | [U] |
| ISRO Chandrayaan-3 | LPDC images matched against an onboard reference map for position; LHDAC used for hazard detection | [V] |
| Chang'E crater-based registration; HiRISE/CTX/HRSC control networks | Plausible but not confirmed in our checks | [U] |
| Caltech COSI-Corr, AROSICS | Sub-pixel optical correlation and multi-sensor co-registration (Earth observation) | [V] |

**Lessons we take from them.**
1. Agencies with accuracy requirements use geometry, altimetry-derived DEMs and control networks. Pure image matching is a fallback.
2. Crater-based features are a proven illumination-robust anchor for lunar navigation. [V] SLIM
3. Rendering a DEM under the image's lighting is an accepted lunar technique. [V] Liu et al. 2024
4. Validation uses independent references (LOLA tracks, simulated truth). We follow that.

---

## 5. System architecture

### 5.1 Principles

1. **Scientific data first.** Keep the array, the label and the geometry together. Do not convert to JPEG for processing. JPEG or PNG are for display only.
2. **Modular stages with typed interfaces.** Each stage reads and writes a defined object and can be replaced.
3. **Everything measured.** Each stage logs counts, time and key statistics.
4. **Two modes.** Research mode (experiments, benchmarks, tracking) and operational mode (one pair in, one product out).
5. **Fail loudly.** Every stage can raise a typed failure that the gate turns into `REGISTRATION FAILED` with a reason.

### 5.2 Stage diagram

```
PDS4 product(s) + reference
        |
[1] INGEST            image array, XML label, geometry files -> Product object
        |
[2] GEOMETRY          SPICE attach -> camera model -> bundle adjustment -> refined model
        |
[3] ORTHORECTIFY      project both images to a common map projection and GSD (DEM if available)
        |
[4] REPRESENT         raw | gradient | phase congruency | local-normalized | rendered reference
        |
[5] MATCH             SIFT/RootSIFT/ASIFT | RIFT | LoFTR | LightGlue | RoMa  (tiled, coarse-to-fine)
        |
[6] ESTIMATE          robust fit; model selection (similarity, affine, projective, local)
        |
[7] SELECT + REFINE   grid-based spatial selection; sub-pixel refinement; uncertainty
        |
[8] GATE              accept -> products + metrics      |   abstain -> reason code
```

### 5.3 Stage specifications

#### Stage 1: Ingest

- **Input:** path to a PDS4 `.xml` label and its `.img` data file (and geometry files if present).
- **Output:** `Product` object with fields: `array` (float32, with mask), `meta` (instrument, product ID, GSD, bit depth, acquisition time), `sun` (azimuth, elevation, incidence, emission, phase if available), `footprint`, `geometry_refs`, `provenance` (file hashes).
- **Notes:** one adapter class per instrument (`OhrcAdapter`, `Tmc2Adapter`, `IirsAdapter`) and per reference (`LroNacAdapter`, `SeleneAdapter`). Adapters must refuse to guess missing metadata; they return `None` and a warning, and the pipeline then drops to a mode that does not need it.
- **IIRS:** the adapter yields a cube `(bands, rows, cols)` plus a `to_image(strategy)` method (strategies in section 7.3).

#### Stage 2: Geometry

- **Input:** `Product` objects.
- **Process:** attach SPICE kernels (ISIS `spiceinit` route per the USGS guide), generate camera models (ISD via `isd_generate`), run bundle adjustment across the source and reference images when both have rigorous camera models.
- **Why:** the Ames Stereo Pipeline example found notable pointing error in OHRC, and bundle adjustment was required. [V]
- **Output:** refined camera models and an estimate of residual image-space error. If no rigorous model exists for a product, record `geometry_quality = none` and use the metadata-only path.

#### Stage 3: Orthorectify

- **Input:** refined camera models, DEM (optional), target projection and GSD.
- **Process:** map-project each image to the same projection, with the common GSD chosen from the coarser image unless an experiment shows otherwise. Apply low-pass filtering before downsampling.
- **Output:** two co-gridded rasters with masks, plus the map-projection parameters. After this stage the unknown transform should be small (mostly residual offset and local distortion). [H] to be measured: we record the residual offset magnitude before and after this stage as an experiment output.

#### Stage 4: Represent

Produces a stack of representations for each image (section 7.4). The matcher adapters decide which one they consume. In render mode, the reference side is replaced by a **rendered image** from a DEM under the source's Sun geometry.

#### Stage 5: Match

- **Input:** source and reference representations.
- **Process:** each matcher adapter implements `match(src, ref, tile_spec) -> Matches` and returns coordinates, scores and descriptors' distances in **original orthorectified pixel coordinates**.
- **Tiling:** images larger than the matcher's practical input are cut into overlapping tiles and matched coarse-to-fine. RoMa's default input is 560 px upsampled to 864 px, so tiling is mandatory for it. [V]
- **Output:** a combined `Matches` table with a `source` column naming the matcher that proposed each correspondence.

#### Stage 6: Estimate

- **Input:** `Matches`.
- **Process:** ratio test (for descriptor matchers), mutual nearest neighbour, then robust fit (MAGSAC++ as the first choice [V as a method]; also RANSAC and others for ablation). Fit similarity, affine and projective models and a local model; choose by information criterion and by hold-out check-point error, **not** by inlier count alone.
- **Output:** transform(s), inlier mask, residuals, model-selection record.

#### Stage 7: Select and refine

- **Spatial selection** (section 7.7): grid quotas so inliers cover the image.
- **Sub-pixel refinement** (section 7.8): local phase correlation, least-squares matching and quadratic peak fitting, compared experimentally.
- **Uncertainty** (section 7.9): per-match and per-transform.

#### Stage 8: Gate

Applies pre-registered acceptance rules (section 7.10). Output is either the product package or an abstention with a reason code.

### 5.4 Operating modes

| Mode | Inputs | Use |
|---|---|---|
| A. Image-only | Two images | Fallback; also the SIH-demo path if metadata are missing |
| B. Metadata-assisted | Images plus SPICE and label geometry | Default for Chandrayaan-2 products |
| C. Terrain-assisted | B plus DEM (TMC-2-derived or LOLA-derived) | Large Sun-angle gaps, parallax, render-and-match |

All three are compared in the experiments. We report which mode each result came from.

### 5.5 Data model

```
Product:      id, instrument, level, array, mask, gsd_m, time, sun{az,el,inc,emi,phase}, footprint, geom_refs, provenance
Matches:      src_xy[N,2], ref_xy[N,2], score[N], matcher[N], tile_id[N], meta
Transform:    kind, params, covariance (optional), fitted_on (match ids)
Registration: transform, inlier_mask, residuals, coverage, refine_log, uncertainty, gate_decision, reason
Metrics:      rmse, mae, median, p95, inlier_count, inlier_ratio, coverage, success, runtime_s, gpu_mem_mb
```

### 5.6 Repository layout

```
lunacorr/
  README.md  LICENSE  pyproject.toml  Dockerfile
  configs/            # YAML per experiment; frozen after pre-registration
  lunacorr/
    io/               # adapters, PDS4 parser, GeoTIFF writers
    geometry/         # ISIS/ASP wrappers, camera models, orthorectification
    represent/        # gradient, phase congruency, normalization, DEM rendering
    match/            # sift.py rift.py loftr.py lightglue.py roma.py base.py
    estimate/         # robust fit, model selection
    refine/           # phase corr, LSM, peak fit
    select/           # spatial selector, coverage metrics
    uncertainty/      # bootstrap, ensembles
    gate/             # acceptance rules, reason codes
    eval/             # metrics, check points, statistics
    synth/            # synthetic transform and illumination generators
    cli.py  api.py
  experiments/        # run records, one folder per experiment ID
  tests/              # unit + regression tests with tiny fixtures
  docs/
  data/               # never committed; .gitignore; scripts to download
```

### 5.7 Experiment tracking

Every run gets an immutable ID such as `EXP-000183` and a record: dataset version, pair ID, preprocessing version, matcher and weights hash, estimator, refinement method, random seed, git commit, container digest, hardware, runtime, metrics, failure reason. A result without a complete record is not used in any claim.

### 5.8 Compute and performance notes [H]

- Large rasters: use windowed reads (GDAL/rasterio), tile caches, and 16-bit or float32 as the label requires.
- GPU: the transformer-based matchers dominate memory; control tile size. We record peak GPU memory per run.
- CPU fallback must exist for SIFT, RIFT and refinement so the demo runs without a GPU.
- No claim about runtime until measured on a named machine.

---

## 6. Geometry cookbook (ISIS and Ames Stereo Pipeline)

Exact command-line flags change between releases. The sequence below follows the USGS and ASP documentation we read. **Before running anything, open the current documentation and copy exact syntax.**

### 6.1 Environment

- Create an isolated conda environment with ISIS 10 or later, `ale`, `usgscsm` and `SpiceQL` as the USGS guides describe. At the time of reading, ISIS 10 was a release candidate. [V]
- Set `ISISROOT` and `ISISDATA`. Download the Chandrayaan-2 SPICE data into the ISIS data area. [V]
- Install the Ames Stereo Pipeline if bundle adjustment and map projection are done with it. [V] it has a Chandrayaan-2 example.

### 6.2 OHRC sequence [V order, flags to confirm]

1. `isisimport` the PDS4 `.xml` and `.img` into a cube. ISIS 10 or later is needed for correct OHRC line-exposure handling.
2. `spiceinit` to attach kernels.
3. `isd_generate` using the `-k` route (USGS notes OHRC differs from TMC-2 here).
4. Write images as **GeoTIFF** for large products, as USGS recommends.
5. Crop to the overlap area with a tool that keeps camera data intact.

### 6.3 TMC-2 sequence [V order, flags to confirm]

1. `isisimport` (template autodetected in ISIS 10+).
2. `isd_generate -s` reading kernels from the local data area.
3. `crop` to the overlap area.

### 6.4 Bundle adjustment [V example]

The ASP example runs `bundle_adjust` on cropped cubes plus their ISD JSON files with `--ip-per-image 30000` and an output prefix, because pointing error was significant. A stereo pair with about 25 degrees of convergence was used there. **Our use differs:** we adjust a source and a reference image that overlap, possibly from different missions, so we must check that enough interest points are found across the two. Record the number of interest points and the post-adjustment residuals as outputs of Stage 2.

### 6.5 Map projection

Use the ASP or ISIS map-projection tools to project each image onto the same grid. [H] tool names `mapproject` (ASP) and `cam2map` (ISIS) per their documentation; confirm. Choose the projection appropriate to the latitude (for example, a local stereographic or equirectangular projection for mid-latitudes). **Polar sites need special care** because of projection distortion.

### 6.6 What to measure here

For every pair, log: residual offset before bundle adjustment, after bundle adjustment, and after orthorectification. This single table tells us how much of the problem geometry removes, which is the central claim of our approach. It is currently **[H]** and must be measured, not asserted.

---

## 7. Algorithm specifications

### 7.1 Notation

`I_s`, `I_r`: source and reference rasters after Stage 3. `(x, y)`: pixel coordinates, pixel centres at integers. `T`: transform from source to reference coordinates. `p_i = (x_i, y_i)` in source, `q_i` in reference.

### 7.2 Resampling to the common grid

- Pick target GSD `g*` (default: the coarser of the two). Experiment with `g*` as a parameter.
- Downsampling: Gaussian low-pass with sigma about `0.5 * g*/g_src` pixels (a standard anti-aliasing rule of thumb [H]) before decimation, or use area averaging.
- Record effective information loss (for example, spectral energy removed) per pair.

### 7.3 IIRS to image strategies [H]

| Strategy | Idea | Risk |
|---|---|---|
| S1: single band | Choose a reflected-light band at the short-wavelength end | Low contrast; band may be noisy |
| S2: band mean | Average over a window of reflected-light bands | Mixes composition effects |
| S3: PCA first components | Use leading principal components | Components are scene-dependent |
| S4: band ratio | Ratio of two bands to suppress illumination | Noise amplification |
| S5: learned embedding | Train a small encoder aligned to optical structure | Needs paired data |

Longer wavelengths include thermal emission, so S1 and S2 should stay in the reflected-light range. [H] Evaluate each on the same pairs; choose on a **validation** set only.

### 7.4 Representations

All are candidates. We measure which helps on which pair type.

1. **Raw intensity** (after radiometric normalization to float32 and robust percentile stretch).
2. **Local normalization:** `J = (I - mu_w) / (sigma_w + eps)` with Gaussian window `w`. Reduces slow brightness trends.
3. **Gradient magnitude and orientation:** Sobel or Scharr after mild smoothing. Orientation sign may flip with illumination reversal, so also test orientation modulo 180 degrees.
4. **Phase congruency:** multi-scale, multi-orientation log-Gabor responses; the maximum-moment map or the RIFT maximum-index map as the feature layer. [V] RIFT uses phase congruency for detection and a maximum-index map for description.
5. **Rendered reference (Mode C):** render the DEM under the source's Sun azimuth and elevation, then match source to the render.
6. **Crater layer (optional):** detect crater rims and use their geometry as stable anchors. [H] motivated by SLIM and the crater-based literature.

### 7.5 Rendering a DEM for render-and-match [H]

For each pixel with surface normal `n` and unit vectors to the Sun `s` and to the camera `v`:
- `mu0 = n . s` (cosine of incidence), `mu = n . v` (cosine of emission).
- Lunar-Lambert style reflectance (standard in planetary photometry): `R = A * [ (1 - w) * mu0 + 2 * w * mu0 / (mu0 + mu) ]`, where `A` is a scale factor and `w` weights the Lommel-Seeliger term, which may depend on phase angle. **Parameter values must come from the literature and be validated; we have not verified them here.**
- Cast shadows by marching along the Sun direction over the DEM and marking pixels whose horizon is above the Sun elevation.
- Limit: the DEM must resolve the shading the image shows. At OHRC scale we usually lack a DEM that fine, so render-and-match is expected to work best at TMC-2 or LRO NAC scale. [H]

### 7.6 Matchers

| Matcher | Input | Settings to record | Notes |
|---|---|---|---|
| ORB | raw/local-norm | n features, scale levels | weak baseline |
| SIFT / RootSIFT | raw/local-norm/gradient | contrast threshold, n octaves, ratio test | serious baseline. RootSIFT: L1-normalize descriptor, take elementwise square root |
| ASIFT | raw | tilt set | affine-invariant; costly |
| RIFT / RIFT2 | phase-congruency layers | scales, orientations | designed for nonlinear radiometric difference |
| LoFTR | raw or local-norm tiles | weights, tile size, confidence threshold | coarse-to-fine transformer |
| LightGlue (with a local feature extractor) | tiles | extractor choice, n keypoints | adaptive depth |
| RoMa | tiles | resolution, certainty threshold | default 560 px to 864 px; dense warp plus certainty |

Rules for every matcher:
1. Same data, same tiles, same metrics, same estimator.
2. Record the pretrained weights' identity and training data. General-photo weights are a hypothesis for lunar use, not a given.
3. Test-time augmentation (matching rotated or rescaled copies and merging) is an optional ablation. [H] no evidence yet for lunar data.

### 7.7 Spatial selection and coverage

**Goal:** uniform distribution of inlier matches across the image. The problem statement requires this. [S] The metric is ours. [M]

**Selector (per image pair after robust fit):**
1. Divide the valid area into an `M x N` grid (default to be tuned; report sensitivity).
2. Score each inlier match: `score = f(matcher confidence, residual, local uniqueness)`.
3. For each cell keep up to `k_max` best matches; require at least `k_min` where the cell contains any candidate.
4. For cells with no candidates, mark `empty` and, if the cell has texture, trigger a **local search** with a smaller tile and a different matcher or representation.
5. Refit using the selected set with spatial weights to avoid a dense cluster dominating the fit.

**Coverage metrics (all [M]):**
- `occupied_ratio = (cells with >= 1 inlier) / (valid cells)`.
- `entropy = - sum_i p_i log(p_i) / log(K)`, where `p_i` is the fraction of inliers in cell `i` and `K` the number of valid cells. 1 means perfectly uniform.
- `largest_empty_circle`: radius of the largest circle in the valid area containing no inlier, as a fraction of the image diagonal.
- Report all three. A single "coverage %" is not enough, because a few points per cell can still leave a large hole.

**Trade-off to measure:** enforcing uniformity may lower the raw inlier ratio or raise RMSE if cells contain poor matches. We report both before and after selection.

### 7.8 Sub-pixel refinement

All three methods run on patches around each selected match, in the orthorectified frame. We compare them.

**(a) Phase correlation.** For patches `f` and `g`, compute `R = F{f} * conj(F{g}) / |F{f} * conj(F{g})|`. The inverse FFT of `R` peaks at the integer shift. Refine the peak by an upsampled DFT or a fit. [V] AROSICS uses phase correlation per moving window for sub-pixel shifts. A Hann window reduces edge effects.

**(b) Quadratic peak fit (1-D along each axis).** With correlation values `c(-1), c(0), c(+1)` around the integer peak: `delta = 0.5 * (c(-1) - c(+1)) / (c(-1) - 2*c(0) + c(+1))`. Pixel-locking bias is known for such fits [H], so compare against (a) and (c).

**(c) Least-squares matching (LSM).** Minimize over affine parameters and radiometric terms:
`sum_window [ I_r(x, y) - (r0 + r1 * I_s(a11*x + a12*y + tx, a21*x + a22*y + ty)) ]^2`
by Gauss-Newton with bilinear or cubic interpolation. Iterate until the update is below a tolerance. The parameter covariance is `sigma0^2 * (A^T A)^(-1)`, which yields a per-match uncertainty. [H] standard photogrammetric method; not verified against a lunar source.

**Iterate:** after refinement, update the transform, re-warp, and repeat while the median update exceeds a tolerance. Log convergence.

**Measuring benefit:** compare error on independent check points with and without refinement, per pair, with distributions (section 9).

### 7.9 Uncertainty

1. **Transform covariance:** bootstrap the inlier set (resample with replacement, refit, `B` times). Report the parameter spread and the induced displacement spread at a grid of image points.
2. **Per-match uncertainty:** from the LSM covariance where available, otherwise from the width of the correlation peak.
3. **Ensemble disagreement:** distance between transforms fitted from different matchers on the same pair. Large disagreement lowers confidence.
4. **Calibration:** check that predicted uncertainty matches actual error on check points (for example, the fraction of check points inside the predicted 95% region). An uncalibrated uncertainty is not reported as a number the user should trust.

### 7.10 Gate: accept or abstain

**Inputs:** inlier count, coverage metrics, residual percentiles, model-selection result, cross-matcher consistency, geometry quality, refinement convergence.

**Rule form:** accept only if all hold: `N_inliers >= N_min`, `occupied_ratio >= c_min`, `largest_empty_circle <= e_max`, `p95_residual <= r_max`, `ensemble_disagreement <= d_max`.

**The thresholds are not set here.** We set them on the **validation** set, write them in the experiment config, freeze them, and only then run the held-out test. Reason codes: `LOW_INLIERS`, `LOW_COVERAGE`, `LARGE_HOLE`, `HIGH_RESIDUAL`, `MATCHER_DISAGREEMENT`, `GEOMETRY_UNRELIABLE`, `NO_OVERLAP`, `REFINEMENT_DIVERGED`.

**Report the abstain rate and what happens to accuracy on accepted pairs** (selective-prediction view). A system that never abstains is not credible.

### 7.11 Robust estimation details

- Candidate estimators: RANSAC, MAGSAC++ [V as method; tested on homography and fundamental matrix fitting], and others for ablation.
- Iterations needed by RANSAC: `N = log(1 - p) / log(1 - w^s)` for confidence `p`, inlier fraction `w`, sample size `s`. Use it to sanity-check iteration budgets.
- Models in increasing flexibility: similarity (4 DOF), affine (6), projective (8), then a local model (for example piecewise affine or thin-plate spline on the inlier set).
- **Selection:** compare by error on held-out check points and by a penalized-likelihood criterion; reject a flexible model that overfits (check-point error rises while fit residual falls).

---

## 8. Data, ground truth and benchmark construction

### 8.1 Ground-truth hierarchy

| Level | Source of truth | Use | Limit |
|---|---|---|---|
| G0 | Synthetic: known transform applied to a real lunar image | Training, controlled tests | Not real sensors or real illumination |
| G1 | Real, same sensor, small change | Development | Ground truth must be established independently |
| G2 | Real, same area under different illumination | Development; illumination robustness | Needs careful co-registration to define truth |
| G3 | Real, cross-sensor | Development; modality robustness | Hardest truth problem |
| G4 | Held-out real scenes never used for tuning | Final claims only | Small; uses frozen system |

### 8.2 Independent check points

The inlier RMSE of the fitted model is **optimistic**, because the model was fitted to those same points. Accuracy must be measured on points not used in estimation.

**Check-point sources:**
1. **Manually picked points** by two analysts independently, with disagreement recorded as the human noise floor.
2. **Altimetry-tied points** (LOLA-derived control) where products are tied to LOLA. [V] NAC and LOLA ties exist in the literature we read.
3. **Synthetic points** (G0) with exact truth.
4. **Cross-product consistency** (for example, a pair of overlapping OHRC images with shared tie points not used in fitting).

**Protocol:** reserve check points before any tuning. Do not look at check-point error while choosing thresholds. Compute the human noise floor first; no claim finer than that floor.

### 8.3 Synthetic generator (G0) levels

| Level | Operation | Purpose |
|---|---|---|
| L1 | Rotation, scale, translation, affine, mild perspective | Basic invariance |
| L2 | Blur, noise, contrast, gamma, stripe artefacts, quantization | Sensor-like degradation |
| L3 | Resolution change with proper anti-aliasing | Scale-gap realism |
| L4 | Shadow and shading change from a DEM re-rendered at a different Sun angle | Illumination realism |
| L5 | Modality simulation (for example, spectral-to-pan mapping for IIRS-like data) | Cross-sensor realism |

**Warning:** scaling brightness (`I2 = 0.7 * I1`) is **not** Sun-angle simulation. Real change moves shadows and reverses slope shading, which needs DEM-based rendering (L4). [H]

### 8.4 Splits and leakage control

- Split by **scene or region**, never by random patch. If two crops of one crater land in training and test, the model has effectively seen the answer.
- All derived versions (synthetic transforms, tiles, augmentations) of a source scene stay in the same split.
- Keep a manifest: scene ID, split, product IDs, generation seed, hash.
- G4 test scenes are locked in a separate manifest with restricted write access. No one tunes on them.

### 8.5 Difficulty taxonomy

Label every pair with measured factors: Sun azimuth difference, Sun elevation difference, incidence-angle difference, GSD ratio, viewing-angle difference, overlap fraction, shadow fraction, texture measure, modality pair. Bin into levels L0 (trivial) to L4 (severe) with bin edges chosen **from the observed distribution**, not guessed. Report results per bin.

### 8.6 Pair ladder

| Level | Pair |
|---|---|
| 1 | OHRC to OHRC |
| 2 | TMC-2 to TMC-2 |
| 3 | OHRC to LRO NAC |
| 4 | TMC-2 to LRO NAC |
| 5 | OHRC to TMC-2 |
| 6 | IIRS to optical reference (using a section 7.3 strategy) |
| 7 | Combined extreme cases |

This ordering isolates variables so a failure can be attributed. [H] experimental design. If levels 5 and 6 fail we report that and investigate; we do not hide it.

---

## 9. Metrics and statistics

### 9.1 Definitions

Let `e_i = || T(p_i) - q_i ||` be the displacement error of check point `i` after registration (pixels in the reference grid; also report metres using the GSD).

| Metric | Definition | Notes |
|---|---|---|
| RMSE | `sqrt( (1/N) * sum e_i^2 )` | Report on check points, and separately on fit inliers (labelled as optimistic) |
| MAE | `(1/N) * sum e_i` | |
| Median error | median of `e_i` | Robust to outliers |
| P95 error | 95th percentile of `e_i` | Tail behaviour |
| Inlier count | matches consistent with the fitted model | Depends on inlier threshold; report threshold |
| Inlier ratio | `N_inliers / N_candidate_matches` | Candidate definition must be stated (after ratio test or before) |
| Coverage | occupied ratio, entropy, largest empty circle (section 7.7) | Our metric [M] |
| Success rate | fraction of pairs accepted by the gate **and** with check-point error under a pre-registered tolerance | Tolerance set before testing |
| Abstain rate | fraction rejected by the gate | |
| Runtime | wall-clock per pair per stage, named hardware | |
| GPU memory | peak MB | |

**Never report only the mean.** Two methods can share a mean and differ in tail risk.

### 9.2 Statistical practice

1. The statistical unit is the **pair** (or the scene), not the individual match. Matches within a pair are correlated.
2. Report medians and percentiles of per-pair metrics, with **bootstrap confidence intervals over scenes**.
3. Compare methods with **paired** tests on the same pairs (for example Wilcoxon signed-rank on per-pair errors), and report effect sizes. State multiple-comparison handling when many methods are compared.
4. Report per-bin results (difficulty levels) and per-pair-type results. An overall average hides failures.
5. State the human noise floor from check-point picking and do not claim errors below it.
6. Pre-register the success definition before the held-out run (template in Appendix C).

### 9.3 What "sub-pixel" will mean in our report

We will write: "On held-out check points of type X (n = ...), the median error was ... px (95th percentile ... px), against a human noise floor of ... px." We will not write "sub-pixel accuracy" as a bare claim. The numbers come from experiments, and any threshold is stated as ours.

---

## 10. Experiment plan

### 10.1 Experiment matrix (to be populated with measured results)

| ID | Pipeline | Question answered |
|---|---|---|
| E0 | Raw images, SIFT, RANSAC, homography | How bad is the naive pipeline? |
| E1 | RootSIFT | Does descriptor normalization help? |
| E2 | Local normalization plus SIFT | Does simple illumination handling help? |
| E3 | Multi-scale SIFT/ASIFT | Does scale and viewpoint handling help? |
| E4 | Orthorectified inputs plus SIFT | **How much does geometry-first help?** (central claim) |
| E5 | E4 plus RIFT / phase-congruency features | Does illumination-robust representation help beyond geometry? |
| E6 | E4 plus pretrained LoFTR | Does a learned matcher beat classical here? |
| E7 | E4 plus pretrained LightGlue | same |
| E8 | E4 plus pretrained RoMa (tiled) | same |
| E9 | Best of E5-E8 plus DEM render-and-match (Mode C) | Does physics-based illumination handling help for large Sun-angle gaps? |
| E10 | Best plus spatial selector | Cost and benefit of uniform coverage |
| E11 | Best plus sub-pixel refinement variants (a, b, c) | Which refinement wins, by how much? |
| E12 | Geometric model comparison (similarity, affine, projective, local) | Where does a global model fail? |
| E13 | Gate calibration on validation | Abstain rate versus accepted-pair error |
| E14 | Fine-tuning (only if justified) | Does a lunar-adapted matcher close a measured gap? |
| E15 | Frozen system on G4 held-out scenes | Final claims |

Each row has a results table with the same columns: pair type, difficulty bin, n pairs, median error, P95, inlier ratio, coverage, success rate, abstain rate, runtime.

### 10.2 Test conditions (labels, not results)

| Test | Variable isolated |
|---|---|
| T1 | Same sensor, small illumination change |
| T2 | Same sensor, large illumination change |
| T3 | Scale change only |
| T4 | Viewpoint change only |
| T5 | OHRC to LRO NAC |
| T6 | TMC-2 to LRO NAC |
| T7 | IIRS to optical reference |
| T8 | Illumination plus scale |
| T9 | Viewpoint plus illumination |
| T10 | Low-texture terrain |

### 10.3 Ablation rules

- Change **one thing at a time** between consecutive experiments.
- Keep all matchers on the same tiles and the same robust estimator when comparing matchers.
- Run each stochastic method with multiple seeds and report variability.
- If SIFT beats a learned matcher on a bin, report it and keep the classical method for that bin.

### 10.4 Decision tree after baselines

```
E0-E4 results
  |-- geometry-first closes most of the gap  -> keep simple matchers; invest in selection, refinement, gate
  |-- large Sun-angle gap remains            -> invest in E5 and E9
  |-- modality gap remains (IIRS)            -> separate IIRS track, S1-S5 strategies
  |-- learned matchers beat classical        -> keep as ensemble member; test fine-tuning
  |-- learned matchers do not beat classical -> do not train a custom model "for AI's sake"
```

---

## 11. Training and fine-tuning plan (only if justified)

### 11.1 Gate for training

Train or fine-tune **only if** E6-E9 leave a measured gap on real validation data, and E4 and E5 cannot close it. The decision and its evidence are written in the experiment log.

### 11.2 Data

- Training pairs: G0 synthetic from training-split scenes (levels L1-L4), plus real pairs from training-split scenes where truth is established.
- Validation: real pairs from validation-split scenes. Test: G4 only, untouched.
- Augmentation inspired by XoFTR's use of pseudo-modality augmentation for thermal-visible training: simulate modality or illumination change in training images. [V] XoFTR does this for thermal; our version for lunar illumination (L4) and IIRS-like data (L5) is [H].

### 11.3 Model options

1. **Fine-tune a pretrained matcher** (LoFTR, LightGlue, RoMa) with a correspondence loss on ground-truth warps, freezing early layers first, and unfreezing gradually.
2. **Train a small cross-sensor encoder** that maps OHRC, TMC-2 and IIRS representations to a shared feature space for descriptor matching. [H] research direction; high risk.
3. **Learned confidence head** to predict per-match reliability, feeding the gate.

Hyperparameters (learning rate, batch size, epochs, crop size) are chosen on the validation set and recorded; we do not quote starting values as results.

### 11.4 What we will not train

An end-to-end network that takes two images and outputs a warped image. It is hard to validate, hard to diagnose, and does not guarantee uniform match distribution. We learn **correspondence** and keep geometry and optimization explicit.

### 11.5 Overfitting checks

Compare synthetic-validation and real-validation performance. A model that excels on synthetic data but not real data has learned the generator. Report both.

---

## 12. Delivery plan, roles and timeline

### 12.1 Roles (rename to match the actual team)

| Role | Responsibilities |
|---|---|
| Technical lead / architect | Interfaces, integration, experiment governance |
| Data and geometry engineer | PRADAN access, PDS4, ISIS/ASP, bundle adjustment, orthorectification |
| Computer-vision engineer | Representations, classical matchers, estimators, selector, refinement |
| ML engineer | Learned matchers, tiling, fine-tuning if justified, uncertainty |
| Evaluation and QA lead | Benchmark, check points, statistics, leakage control, red-team |
| Frontend and demo engineer | UI, visualization, packaging |
| Literature and documentation lead | Source verification, deck, this document |

### 12.2 Phases (relative weeks; adjust to the real SIH calendar)

| Phase | Weeks | Output | Gate to continue |
|---|---|---|---|
| 0 Requirements | 0-1 | Frozen requirement matrix; helpdesk questions sent | Questions logged |
| 1 Data audit | 1-3 | Pair inventory; ISIS ingest works for OHRC and TMC-2 | At least one real pair imported end to end |
| 2 Geometry | 3-5 | Bundle adjustment and orthorectification on pilot pairs; offset-reduction table | Table filled |
| 3 Baselines | 4-6 | E0-E4 on pilot pairs | Baseline metrics reproducible |
| 4 Matchers | 5-8 | E5-E8 | Failure analysis written |
| 5 Selection, refinement, gate | 7-10 | E10-E13 | Gate calibrated on validation |
| 6 Optional training | 9-12 | E14 | Only if section 11.1 gate passed |
| 7 Frozen final test | 12-13 | E15 | Thresholds frozen before run |
| 8 Packaging and demo | 12-14 | Container, README, UI, final report | Fresh-machine install works |

These durations are planning guesses [H], not estimates derived from data.

### 12.3 Minimum viable submission

If time runs short, the minimum that remains honest is: PDS4 ingest, geometry-first pipeline with SIFT/RootSIFT and MAGSAC++, spatial selector, one sub-pixel refinement method, check-point evaluation on a small set of real pairs, abstain gate, and a clear statement of what was and was not tested.

---

## 13. Software, API and UI

### 13.1 Stack [M]

Python for the core (rasterio/GDAL, NumPy, SciPy, OpenCV, scikit-image, PyTorch for learned matchers), ISIS/ASP via subprocess wrappers, FastAPI for the service, a React or Next.js frontend with a map or image viewer. Container image for reproducibility. CPU-only fallback.

### 13.2 CLI

```
lunacorr register --source S.xml --reference R.xml --mode B --config configs/final.yaml --out out/
lunacorr evaluate --run out/ --checkpoints cp.csv
lunacorr bench   --manifest manifests/val.yaml --config configs/e6.yaml
```

### 13.3 Output package

`registered_image.tif`, `match_points.csv`, `error_map.tif`, `uncertainty.tif`, `result.json`, `processing_log.json`.

`match_points.csv` columns: `id, src_x, src_y, ref_x, ref_y, matcher, confidence, residual_px, refine_delta_px, uncertainty_px, status(accepted|rejected), cell_id`.

`result.json` fields: `source_id, reference_id, mode, geometry_quality, transform{kind,params}, metrics{rmse,mae,median,p95,inlier_count,inlier_ratio,occupied_ratio,entropy,largest_empty_circle}, checkpoint_metrics (if provided), gate{decision,reason}, runtime_s, versions{code,deps,weights}, dataset_version`.

### 13.4 UI screens (secondary to the engine)

1. Select source and reference; show footprints and metadata (Sun angles, GSD).
2. Run view: stage progress with counts (features, candidates, inliers).
3. Side-by-side with match lines; click a match to see matcher, confidence, residual, refinement delta, uncertainty.
4. Registered overlay with opacity slider; error map; coverage grid.
5. Metrics panel and gate decision with reason.
6. Export.

**UI honesty rules:** do not display placeholder numbers; metrics shown must come from the run. If check points are absent, label the displayed error as fit residual, not accuracy.

### 13.5 Testing

- Unit tests for each stage with tiny fixtures; property tests that known transforms are recovered on synthetic pairs.
- Regression tests: a small set of pairs with stored expected metrics within tolerances.
- Determinism: seeds fixed; nondeterministic GPU operations noted.
- CI builds the container and runs the small test set.

---

## 14. Risk register

| Risk | Likelihood / impact (qualitative) | Mitigation | Early signal |
|---|---|---|---|
| SIH dataset arrives late or in an unexpected format | Medium / High | Adapter layer; build on public PRADAN data now | Dataset still TBD close to the deadline |
| ISIS 10 or SPICE ingest problems for some products | Medium / High | Test on pilot products in week 1; fall back to Mode A | Import errors in the data audit |
| Raw pointing error too large for any matcher | Medium / High | Bundle adjustment; coarse global search; pyramid | Offset after orthorectification remains large |
| Illumination gap defeats all feature matchers | Medium / High | Render-and-match; phase-based features; crater anchors | E5-E8 fail on T2, T8 |
| Learned matchers do not transfer | Medium / Medium | Keep classical baseline; ensemble; fine-tune only if justified | E6-E8 below SIFT |
| IIRS unmatched | High / Medium | Separate track; report honestly | S1-S5 all fail on T7 |
| No trustworthy ground truth | High / High | Hierarchy G0-G4; manual check points with noise floor | Analysts disagree beyond the target error |
| Uniformity requirement hurts accuracy | Medium / Medium | Report trade-off; local re-search in empty cells | Coverage up, P95 error up |
| Compute limits (memory, time) | Medium / Medium | Tiling, CPU fallbacks, caching | Out-of-memory on full products |
| Data licence breach | Low / High | Do not redistribute; scripts only | Raw files in the repo |
| Overclaiming in the pitch | Medium / High | Claim ledger (section 15); QA review | Any number without an experiment ID |
| Competing public implementations | High / Low | Differentiate on method, measurement and honesty, not on a dashboard | n/a |

---

## 15. Pitch, claim ledger and judge Q&A

### 15.1 Slide-by-slide source map

| Slide | Content | Backed by (section) |
|---|---|---|
| 1 Title | PS 26166, theme, category, org; team fields left for portal | 1, 0.2 |
| 2 Idea | Problem, solution, distinctives; supported / proposed / not established | 3, 4, 5 |
| 3 Technical approach | Eight stages; benchmark ladder; modes; outputs | 5, 7, 10 |
| 4 Feasibility | In hand, engineering work, open validation; validation ladder; risks | 2, 8, 10, 14 |
| 5 Impact | Users, benefits, safeguards; workflow; social, economic, environmental | 13, 14 |
| 6 References | Evidence summary and selected references | 4 |

### 15.2 Claim ledger

| Claim we may make | Basis |
|---|---|
| Chandrayaan-2 OHRC, TMC-2 and IIRS data are public in PDS4 through PRADAN | [V] ISRO archive |
| OHRC about 0.25 m (source discrepancy noted), TMC-2 5 m, IIRS about 80 m with about 256 bands | [V] |
| ISIS 10+ and ASP can ingest and process Chandrayaan-2 products | [V] USGS, ASP docs |
| Large illumination change can break conventional lunar matching | [V] ISPRS 2020 |
| LOLA DEM rendered under NAC lighting has been matched to NAC images | [V] Liu et al. 2024 |
| Mars 2020 resampled descent images to the map frame before matching | [V] JPL |
| Our pipeline is a proposed architecture | Design |

| Claim we must **not** make | Reason |
|---|---|
| Any RMSE, accuracy, inlier ratio, or "sub-pixel achieved" | No experiment |
| LoFTR, LightGlue or RoMa work on Chandrayaan-2 | Not tested; general-photo evidence only |
| IIRS registration works | Not tested |
| Homography is sufficient | Contradicted by relief physics unless shown |
| ISRO requires a particular accuracy | Not stated in the PS |
| ISRO approved or endorsed our design | Not true |
| Our dataset size or number of pairs | Not yet measured |
| Another paper's benchmark numbers as our expectation | Different method and data |

### 15.3 Judge Q&A bank (honest answers)

1. **Why not just use SIFT and RANSAC?** We do, as the baseline. We then measure whether geometry-first processing, illumination-robust features or learned matchers beat it. Recent lunar work has used SIFT successfully in some settings [H, not re-verified], so we will not assume it fails.
2. **What accuracy do you achieve?** We have not run experiments on Chandrayaan-2 data yet. The submission is a validated design, a verified data path, and a measurement plan.
3. **What is your sub-pixel threshold?** The problem statement does not give one. We report error distributions on independent check points and state the human noise floor.
4. **How do you handle different Sun angles?** Three ways to be tested: orthorectify first, illumination-robust representations such as phase congruency (RIFT), and rendering a DEM under the source's lighting, which has lunar precedent [V].
5. **How do you handle IIRS?** It is a separate, last-stage track. We reduce the cube to an image with several strategies and report honestly if none works.
6. **Why not train a neural network on everything?** There is no labelled lunar training set, and synthetic data cannot validate real performance. We train only if a measured gap remains.
7. **How do you get ground truth?** A hierarchy from exact synthetic truth to held-out real scenes with independent check points, and a measured human noise floor.
8. **How do you ensure uniform distribution?** A grid-based selector with quotas and local re-search, and three coverage metrics, with the accuracy trade-off reported.
9. **What if registration fails?** The gate abstains with a reason code. A system that always answers is unsafe for scientific use.
10. **Is a single homography enough?** Not assumed. Lunar relief causes parallax, so the model is chosen by evidence, with local and DEM-assisted options.
11. **What if the SIH dataset is different from public data?** The adapter layer isolates format differences; the evaluation harness is dataset-agnostic.
12. **Does this use ISRO mission data legally?** PRADAN data are free for non-profit scientific use, and ISRO retains ownership. We do not redistribute raw data.
13. **What is new here?** A measured combination: geometry-first processing, illumination-aware matching, spatial uniformity enforcement, sub-pixel refinement, and an abstain gate, with a reproducible benchmark. We do not claim any single component is new.
14. **How is this different from other SIH26166 repositories?** We cannot judge their performance. Our differentiator is the measurement protocol and the honesty of the claims.
15. **How long does it take to run?** Not measured yet. We will report per-stage time on named hardware.
16. **What if bundle adjustment cannot link the two images?** We fall back to metadata-only geometry (Mode B without BA) or image-only (Mode A) and record the reduced geometry quality in the output.
17. **What do you do about low-texture terrain?** Coarser scales, dense matchers and local re-search; if coverage stays low, the gate abstains.
18. **Why trust your uncertainty values?** We calibrate them on check points and report calibration; uncalibrated values are not shown as probabilities.

---

## 16. Open questions and action list

| # | Item | Owner | Status |
|---|---|---|---|
| 1 | Obtain team ID and registered team name from the portal and fill slide 1 | Docs lead | Open |
| 2 | Ask SIH helpdesk: numeric sub-pixel definition, "uniform distribution" definition, evaluation procedure, sensor pairs, runtime limits | Technical lead | Open |
| 3 | Register on PRADAN; download pilot OHRC, TMC-2, IIRS products | Data engineer | Open |
| 4 | Confirm current ISIS release and install on the team machines | Data engineer | Open |
| 5 | Verify the unverified papers in section 4.2 and add DOIs and authors for source [4] | Literature lead | Open |
| 6 | Build the pair inventory and fix difficulty bin edges | Evaluation lead | Open |
| 7 | Decide the common GSD policy and test it as a parameter | CV engineer | Open |
| 8 | Collect LOLA and SELENE products to use as reference and check-point sources | Data engineer | Open |
| 9 | Verify photometric model parameters from the literature before rendering | CV engineer | Open |
| 10 | Confirm ISRO-to-JAXA SLIM image statement before citing | Literature lead | Open |
| 11 | Update slide 4 if any experiment has already been run | Technical lead | Open |

---

## Appendix A: Glossary

- **GSD:** ground sampling distance, metres per pixel.
- **PDS4:** Planetary Data System version 4, the archive standard used for Chandrayaan-2 public data.
- **SPICE:** NASA NAIF observation geometry system (kernels for ephemeris, pointing and instrument).
- **ISIS / ISD:** USGS Integrated Software for Imagers and Spectrometers; image support data used by camera models.
- **LOLA:** Lunar Orbiter Laser Altimeter on LRO; source of lunar topography control.
- **NAC:** Narrow Angle Camera on LRO.
- **Bundle adjustment:** joint refinement of camera parameters and tie-point positions to minimize image-space residuals.
- **Orthorectification:** projecting an image onto a map surface using a camera model and a terrain model.
- **Homography:** projective transform between two views of a plane.
- **Phase congruency:** a measure of feature significance based on frequency-domain phase alignment, robust to illumination and contrast changes.
- **Inlier:** a match consistent with the fitted model within a threshold.
- **Photoclinometry:** estimating surface slopes from image brightness using a reflectance model.
- **SPC (stereophotoclinometry):** combining stereo with photoclinometry to build terrain models and landmark maps.

## Appendix B: Data audit table template

`product_id | instrument | level | width | height | bit_depth | units | nodata | gsd_label_m | gsd_nominal_m | time | sun_az | sun_el | incidence | emission | phase | footprint | overlap_with(ref_id) | geometry_files | dem_available | isis_import(pass/fail) | notes`

## Appendix C: Pre-registration template (fill before any held-out run)

```
Experiment ID:
Date and git commit:
Hypothesis:
Data: manifest hash, split, number of scenes and pairs
Methods compared (with weights hashes):
Primary metric:
Secondary metrics:
Success definition (tolerance, per-pair rule, aggregate rule):
Gate thresholds (frozen values from validation):
Statistical test and confidence interval method:
Check-point source and noise floor:
Exclusion rules (decided now, not later):
What result would falsify the hypothesis:
Signed off by (QA lead):
```

## Appendix D: Experiment log template

`exp_id | date | commit | container_digest | dataset_version | pair_id | pair_type | difficulty_bin | mode | geometry_quality | representation | matcher | weights_hash | estimator | model_selected | selector_params | refinement | gate_decision | reason | rmse_px | median_px | p95_px | inlier_count | inlier_ratio | occupied_ratio | entropy | largest_empty_circle | runtime_s | gpu_mem_mb | notes`

## Appendix E: Check-point protocol

1. Two analysts independently pick `n` distinct, well-defined features per pair in both images (crater rim intersections, boulder tops where stable, sharp albedo boundaries). Avoid shadow edges.
2. Pick before seeing any algorithm output.
3. Compute analyst disagreement to estimate the human noise floor.
4. Store points in the reference grid and the source grid with feature type labels.
5. Exclude check points from any fitting or tuning.
6. Report error by feature type.

## Appendix F: Reference list (verified items only)

[1] ISRO / ISSDC. Chandrayaan-2 Science Data Archive (PRADAN). OHRC, TMC-2, IIRS documentation and PDS4 products.
[2] NASA Ames Stereo Pipeline documentation, Chandrayaan-2 example. USGS ISIS Chandrayaan-2 ingestion guides.
[3] USGS Astrogeology. Chandrayaan 2 mission page.
[4] An integrated photogrammetric and photoclinometric approach for illumination-invariant pixel-resolution 3D mapping of the lunar surface. ISPRS J. Photogramm. Remote Sens., 2020. (authors and DOI to be added)
[5] Liu P, Geng X, Wang Y, Zhang J. LOLA DEM assisted photogrammetric processing of Lunar Reconnaissance Orbiter NAC images for the lunar south pole. ISPRS Archives XLVIII-1, 2024, 409-416. doi:10.5194/isprs-archives-XLVIII-1-2024-409-2024
[6] Haase I, Gläser P, Oberst J. Bundle adjustment of spaceborne double-camera push-broom imagers and its application to LROC NAC imagery. ISPRS Archives XLII-2/W13, 2019, 1397-1404. doi:10.5194/isprs-archives-XLII-2-W13-1397-2019
[7] Li J et al. RIFT: multi-modal image matching based on radiation-variation insensitive feature transform. IEEE Trans. Image Process. 29, 2020, 3296-3310. doi:10.1109/TIP.2019.2959244 (check author list on the publisher page)
[8] NASA/JPL. Mars 2020 Terrain Relative Navigation and Lander Vision System (JPL project page); Mars 2020 Lander Vision System flight performance (NASA NTRS 20230006986); Making an onboard reference map from MRO/CTX imagery for the Mars 2020 Lander Vision System, Earth and Space Science, 2021.
[9] Sun J et al. LoFTR: detector-free local feature matching with transformers. CVPR 2021. Lindenberger P et al. LightGlue: local feature matching at light speed. ICCV 2023. Edstedt J, Sun Q, Bökman G, Wadenbäck M, Felsberg M. RoMa: robust dense feature matching. CVPR 2024, 19790-19800.
[10] Barath D, Noskova J, Ivashechkin M, Matas J. MAGSAC++, a fast, reliable and accurate robust estimator. CVPR 2020.
[11] Scheffler D et al. AROSICS: an automated and robust open-source image co-registration software for multi-sensor satellite data. Remote Sensing 2017, 9(7), 676. Leprince S et al. Co-registration of optically sensed images and correlation (COSI-Corr). IEEE 2009.
[12] Tuzcuoğlu Ö, Köksal A, Sofu B, Kalkan S, Alatan AA. XoFTR: cross-modal feature matching transformer. CVPR Workshops 2024, 4275-4286.
[13] JAXA. SLIM landing descent results (January 2024 press material); Fukuda S et al., Landing results of SLIM using optical navigation, IDW 2024 (crater-based optical navigation).
[14] Adam CD et al. Stereophotoclinometry for OSIRIS-REx spacecraft navigation. Planetary Science Journal, 2023. Gaskell RW et al. Stereophotoclinometry on the OSIRIS-REx mission: mathematics and methods. Planetary Science Journal 4(4), 2023.
[15] ISRO. Chandrayaan-3 lander sensors (LPDC, LHDAC), ISRO release material, August 2023.
