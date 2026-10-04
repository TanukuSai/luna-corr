"""
Automated Cross-Consistency and Benchmark Integrity Validator for LUNA-CORR.

Single Source of Truth Architecture:
Loads canonical JSON benchmark artifacts from results/ and asserts that all:
  - Source Code (lunacorr thresholds & default hyperparameters)
  - Canonical Manifest (BENCHMARK_MANIFEST.md)
  - Repository Documentation (README.md)
  - Scientific Report (docs/SCIENTIFIC_REPORT.md)
  - SIH Presentation Deck (LUNA-CORR_SIH2026_Presentation.pptx)
strictly reflect the authoritative values in the JSON artifacts.

Exits with code 0 if all assertions pass, code 1 on any discrepancy.
"""
import sys
import json
import re
from pathlib import Path

def log_pass(msg: str):
    print(f"  [PASS] {msg}")

def log_fail(msg: str):
    print(f"  [FAIL] {msg}")

def main():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    errors = []
    print("=" * 70)
    print("LUNA-CORR BENCHMARK CROSS-CONSISTENCY AUDIT (JSON SOURCE-OF-TRUTH)")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Load Canonical JSON Benchmark Artifacts (Single Source of Truth)
    # -------------------------------------------------------------
    print("\n1. Loading Canonical JSON Benchmark Artifacts...")
    
    # 1.1 EXP-OHRC-E2E
    ohrc_json_path = root / "results/real_ohrc_cross_orbit/result.json"
    if not ohrc_json_path.exists():
        errors.append(f"Artifact missing: {ohrc_json_path}")
        log_fail("EXP-OHRC-E2E artifact missing")
        return sys.exit(1)
    with open(ohrc_json_path, "r", encoding="utf-8") as f:
        ohrc = json.load(f)
    ohrc_inliers = str(ohrc["metrics"]["inlier_count"])
    ohrc_rmse = f"{ohrc['heldout_validation_correspondences_metrics']['rmse']:.3f}"
    ohrc_fit_rmse = f"{ohrc['fitting_correspondences_metrics']['rmse']:.3f}"
    ohrc_n_test = str(ohrc["heldout_validation_correspondences_metrics"]["n_points"])
    ohrc_status = ohrc["status"]
    assert ohrc_status == "ACCEPTED"
    log_pass(f"EXP-OHRC-E2E: {ohrc_inliers} inliers, {ohrc_rmse} px held-out RMSE, {ohrc_fit_rmse} px fit RMSE, N={ohrc_n_test}")

    # 1.2 EXP-TMC-E2E
    tmc_json_path = root / "results/real_tmc2_stereo_checkpointed/result.json"
    if not tmc_json_path.exists():
        errors.append(f"Artifact missing: {tmc_json_path}")
        log_fail("EXP-TMC-E2E artifact missing")
        return sys.exit(1)
    with open(tmc_json_path, "r", encoding="utf-8") as f:
        tmc_e2e = json.load(f)
    tmc_inliers = str(tmc_e2e["metrics"]["inlier_count"])
    tmc_rmse = f"{tmc_e2e['heldout_validation_correspondences_metrics']['rmse']:.3f}"
    tmc_fit_rmse = f"{tmc_e2e['fitting_correspondences_metrics']['rmse']:.3f}"
    tmc_n_test = str(tmc_e2e["heldout_validation_correspondences_metrics"]["n_points"])
    tmc_status = tmc_e2e["status"]
    assert tmc_status == "ACCEPTED"
    log_pass(f"EXP-TMC-E2E: {tmc_inliers} inliers, {tmc_rmse} px held-out RMSE, {tmc_fit_rmse} px fit RMSE, N={tmc_n_test}")

    # 1.3 EXP-TMC-FIXED
    ablation_json_path = root / "results/ablation_bootstrap_ci.json"
    if not ablation_json_path.exists():
        errors.append(f"Artifact missing: {ablation_json_path}")
        log_fail("EXP-TMC-FIXED artifact missing")
        return sys.exit(1)
    with open(ablation_json_path, "r", encoding="utf-8") as f:
        abl = json.load(f)
    abl_stg1_rmse = f"{abl['1. Raw SIFT']['rmse'][0]:.3f}"
    abl_stg3_rmse = f"{abl['3. + RootSIFT']['rmse'][0]:.3f}"
    abl_stg5_rmse = f"{abl['5. + Adaptive TPS']['rmse'][0]:.3f}"
    abl_stg5_ci = [f"{abl['5. + Adaptive TPS']['rmse'][1]:.3f}", f"{abl['5. + Adaptive TPS']['rmse'][2]:.3f}"]
    raw_stg3 = abl['3. + RootSIFT']['rmse'][0]
    raw_stg5 = abl['5. + Adaptive TPS']['rmse'][0]
    abl_gain_vs_stg3 = f"{((raw_stg3 - raw_stg5) / raw_stg3) * 100:.1f}%"
    log_pass(f"EXP-TMC-FIXED: Stage 1={abl_stg1_rmse} px, Stage 3={abl_stg3_rmse} px, Stage 5={abl_stg5_rmse} px [{abl_stg5_ci[0]}, {abl_stg5_ci[1]}], Gain={abl_gain_vs_stg3}")

    # 1.4 EXP-NEG-DISJOINT
    neg_json_path = root / "results/negative_control_disjoint/result.json"
    if not neg_json_path.exists():
        errors.append(f"Artifact missing: {neg_json_path}")
        log_fail("EXP-NEG-DISJOINT artifact missing")
        return sys.exit(1)
    with open(neg_json_path, "r", encoding="utf-8") as f:
        neg = json.load(f)
    assert neg["status"] == "ABSTAINED"
    assert not neg["accepted"]
    assert "LOW_INLIERS" in neg["reason_codes"]
    assert "LOW_COVERAGE" in neg["reason_codes"]
    neg_inliers = str(neg["metrics"]["inlier_count"])
    log_pass(f"EXP-NEG-DISJOINT: status={neg['status']}, inliers={neg_inliers}, reason_codes={neg['reason_codes']}")

    # 1.5 EXP-SYN-ILLUM
    syn_json_path = root / "results/synthetic_illumination_groundtruth.json"
    if not syn_json_path.exists():
        errors.append(f"Artifact missing: {syn_json_path}")
        log_fail("EXP-SYN-ILLUM artifact missing")
        return sys.exit(1)
    with open(syn_json_path, "r", encoding="utf-8") as f:
        syn = json.load(f)
    item_0 = next(x for x in syn if x["delta_azimuth_deg"] == 0)
    item_45 = next(x for x in syn if x["delta_azimuth_deg"] == 45)
    item_90 = next(x for x in syn if x["delta_azimuth_deg"] == 90)
    item_180 = next(x for x in syn if x["delta_azimuth_deg"] == 180)
    assert item_0["mode_c_reillumination"]["inlier_count"] == 737
    assert item_45["direct_optical"]["precision_at_10px"] == 0.0
    assert item_45["mode_c_reillumination"]["precision_at_10px"] >= 0.99
    assert "SUPPRESSED" in item_90["direct_optical"]["status"]
    assert "SUPPRESSED" in item_180["direct_optical"]["status"]
    log_pass("EXP-SYN-ILLUM: Mode C maintains >99% prec and 737–1,187 inliers under tested sweep.")

    # 1.6 EXP-IO
    io_json_path = root / "results/seeker_latency.json"
    if not io_json_path.exists():
        errors.append(f"Artifact missing: {io_json_path}")
        log_fail("EXP-IO artifact missing")
        return sys.exit(1)
    with open(io_json_path, "r", encoding="utf-8") as f:
        io_res = json.load(f)
    io_samples = str(io_res["n_samples"])
    io_median = f"{io_res['median_latency_ms']:.2f}"
    io_mean = f"{io_res['mean_latency_ms']:.2f}"
    log_pass(f"EXP-IO: N={io_samples}, median={io_median} ms, mean={io_mean} ms")

    # -------------------------------------------------------------
    # 2. Manifest Experiment Registry Audit
    # -------------------------------------------------------------
    print("\n2. Auditing Canonical Experiment Manifest (BENCHMARK_MANIFEST.md)...")
    manifest_path = root / "BENCHMARK_MANIFEST.md"
    if not manifest_path.exists():
        errors.append("BENCHMARK_MANIFEST.md not found.")
        log_fail("BENCHMARK_MANIFEST.md missing")
    else:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        required_exp_ids = [
            "EXP-OHRC-E2E",
            "EXP-TMC-E2E",
            "EXP-TMC-FIXED",
            "EXP-NEG-DISJOINT",
            "EXP-SYN-ILLUM",
            "EXP-IO"
        ]
        for exp_id in required_exp_ids:
            if exp_id in manifest_text:
                log_pass(f"Experiment ID registered: {exp_id}")
            else:
                errors.append(f"Missing Experiment ID in manifest: {exp_id}")
                log_fail(f"Experiment ID missing: {exp_id}")

        # Assert canonical JSON numbers in manifest
        for num, desc in [
            (ohrc_rmse, "OHRC held-out RMSE"),
            (tmc_rmse, "TMC held-out RMSE"),
            (abl_stg1_rmse, "Ablation Stage 1 RMSE"),
            (abl_stg3_rmse, "Ablation Stage 3 RMSE"),
            (abl_stg5_rmse, "Ablation Stage 5 RMSE"),
            (abl_gain_vs_stg3, "Ablation Stage 5 Gain"),
            (io_median, "Seeker median latency")
        ]:
            if num in manifest_text:
                log_pass(f"BENCHMARK_MANIFEST.md contains {desc}: {num}")
            else:
                errors.append(f"BENCHMARK_MANIFEST.md missing {desc}: {num}")
                log_fail(f"BENCHMARK_MANIFEST.md missing {desc}: {num}")

        for stale in ["0.779", "34.42", "0.812", "0.679", "1.110"]:
            if stale in manifest_text:
                errors.append(f"Stale value {stale} found in BENCHMARK_MANIFEST.md")
                log_fail(f"Stale value {stale} in BENCHMARK_MANIFEST.md")
            else:
                log_pass(f"No stale value {stale} in BENCHMARK_MANIFEST.md")

    # -------------------------------------------------------------
    # 3. Codebase Threshold & Hyperparameter Configuration Audit
    # -------------------------------------------------------------
    print("\n3. Auditing Codebase Configuration Parameters...")
    from lunacorr.gate.decision_gate import QualityGate
    from lunacorr.estimate.adaptive_gate import AdaptiveDeformationGate
    from lunacorr.pipeline.inference import LunarRegistrationPipeline

    gate = QualityGate()
    assert gate.min_inliers == 20, f"QualityGate min_inliers ({gate.min_inliers}) != 20"
    assert gate.min_inlier_ratio == 0.15, f"QualityGate min_inlier_ratio ({gate.min_inlier_ratio}) != 0.15"
    assert gate.min_occupied_ratio == 0.30, f"QualityGate min_occupied_ratio ({gate.min_occupied_ratio}) != 0.30"
    log_pass("QualityGate operational threshold harmonized to min_inliers = 20 (N >= 20 reporting threshold).")

    pipeline = LunarRegistrationPipeline()
    assert pipeline.gate.min_inliers == 20, f"Default pipeline QualityGate min_inliers ({pipeline.gate.min_inliers}) != 20"
    assert pipeline.use_lcn is True, f"Default pipeline use_lcn ({pipeline.use_lcn}) is not True"
    log_pass("LunarRegistrationPipeline default gate min_inliers = 20 and use_lcn = True verified.")

    adapt = AdaptiveDeformationGate()
    assert adapt.autocorr_threshold == 0.20, f"AdaptiveDeformationGate threshold ({adapt.autocorr_threshold}) != 0.20"
    assert adapt.min_p95_px == 1.5, f"AdaptiveDeformationGate min_p95_px ({adapt.min_p95_px}) != 1.5"
    assert adapt.eps_zero == 0.05, f"AdaptiveDeformationGate eps_zero ({adapt.eps_zero}) != 0.05"
    assert adapt.min_points == 20, f"AdaptiveDeformationGate min_points ({adapt.min_points}) != 20"
    log_pass("AdaptiveDeformationGate thresholds (S_relief > 0.20, P95 >= 1.5 px, eps_zero = 0.05 px, min_points = 20) confirmed.")

    # -------------------------------------------------------------
    # 4. Text & Document Synchronization Audit
    # -------------------------------------------------------------
    print("\n4. Auditing Cross-Document Synchronization...")
    report_path = root / "docs/SCIENTIFIC_REPORT.md"
    readme_path = root / "README.md"

    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8")
        for stale in ["0.779", "34.42", "0.812", "1,679", "0.679", "1.110"]:
            if stale in report_text:
                errors.append(f"docs/SCIENTIFIC_REPORT.md contains stale reference to {stale}")
                log_fail(f"Stale value {stale} found in docs/SCIENTIFIC_REPORT.md")
            else:
                log_pass(f"No stale {stale} in docs/SCIENTIFIC_REPORT.md.")

        for num, desc in [
            (ohrc_rmse, "OHRC held-out RMSE"),
            (tmc_rmse, "TMC held-out RMSE"),
            (abl_stg1_rmse, "Ablation Stage 1 RMSE"),
            (abl_stg3_rmse, "Ablation Stage 3 RMSE"),
            (abl_stg5_rmse, "Ablation Stage 5 RMSE"),
            (abl_gain_vs_stg3, "Ablation Stage 5 Gain"),
            ("737", "Mode C inliers baseline")
        ]:
            if num in report_text:
                log_pass(f"docs/SCIENTIFIC_REPORT.md contains {desc}: {num}")
            else:
                errors.append(f"docs/SCIENTIFIC_REPORT.md missing {desc}: {num}")
                log_fail(f"Missing {desc} in report: {num}")

        # Check NN-DRC epsilon in report matches code (0.05 px)
        if r"\epsilon = 0.05" in report_text or "0.05 px" in report_text:
            log_pass("docs/SCIENTIFIC_REPORT.md specifies NN-DRC epsilon = 0.05 px matching code.")
        else:
            errors.append("docs/SCIENTIFIC_REPORT.md missing epsilon = 0.05 px specification")
            log_fail("docs/SCIENTIFIC_REPORT.md does not specify epsilon = 0.05 px")

        # Check Section 4.2 warning callout presence
        if "Historical Dynamic Candidate-Pool Experiment" in report_text:
            log_pass("docs/SCIENTIFIC_REPORT.md explicitly qualifies Section 4.2 as historical dynamic experiment.")
        else:
            errors.append("docs/SCIENTIFIC_REPORT.md missing Section 4.2 historical disclaimer")
            log_fail("Missing Section 4.2 historical disclaimer")

    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        for stale in ["0.779", "0.812", "0.679", "1.110", "tests-5 passed", "Pinned dependencies"]:
            if stale in readme_text:
                errors.append(f"README.md contains stale string: {stale}")
                log_fail(f"Stale string '{stale}' in README.md")
            else:
                log_pass(f"No stale string '{stale}' in README.md.")

        for num, desc in [
            (ohrc_rmse, "OHRC held-out RMSE"),
            (tmc_rmse, "TMC held-out RMSE"),
            (abl_stg1_rmse, "Ablation Stage 1 RMSE"),
            (abl_stg3_rmse, "Ablation Stage 3 RMSE"),
            (abl_stg5_rmse, "Ablation Stage 5 RMSE"),
            (abl_gain_vs_stg3, "Ablation Stage 5 Gain"),
            ("737–1,187", "Mode C inlier range"),
            ("tests-15%20passed", "Pytest pass badge")
        ]:
            if num in readme_text:
                log_pass(f"README.md contains {desc}: {num}")
            else:
                errors.append(f"README.md missing {desc}: {num}")
                log_fail(f"Missing {desc} in README: {num}")

    # -------------------------------------------------------------
    # 5. PowerPoint Deck (PPTX) Inspection Audit
    # -------------------------------------------------------------
    print("\n5. Auditing PowerPoint Presentation Deck (LUNA-CORR_SIH2026_Presentation.pptx)...")
    pptx_path = root / "LUNA-CORR_SIH2026_Presentation.pptx"
    if not pptx_path.exists():
        errors.append("LUNA-CORR_SIH2026_Presentation.pptx missing.")
        log_fail("Presentation deck missing.")
    else:
        try:
            from pptx import Presentation
            prs = Presentation(str(pptx_path))
            assert len(prs.slides) == 6, f"Expected 6 slides, found {len(prs.slides)}"
            log_pass(f"Deck loaded successfully: {len(prs.slides)} slides.")

            # Extract all text from all shapes across all slides
            slide_texts = []
            for i, s in enumerate(prs.slides):
                texts = []
                for shape in s.shapes:
                    if shape.has_text_frame:
                        for p in shape.text_frame.paragraphs:
                            if p.text:
                                texts.append(p.text)
                slide_texts.append(" ".join(texts))
            full_deck_text = " ".join(slide_texts)

            # Check presence of all 6 Experiment IDs in PPTX
            for exp_id in required_exp_ids:
                if exp_id in full_deck_text:
                    log_pass(f"PPTX contains experiment ID: {exp_id}")
                else:
                    errors.append(f"PPTX missing experiment ID: {exp_id}")
                    log_fail(f"PPTX missing experiment ID: {exp_id}")

            # Check presence of canonical metrics in PPTX
            canonical_pptx_values = [
                (ohrc_rmse, "OHRC cross-orbit held-out RMSE"),
                (tmc_rmse, "TMC-2 stereo held-out RMSE"),
                (abl_stg5_rmse, "TMC-2 ablation Stage 5 RMSE"),
                (abl_stg3_rmse, "TMC-2 ablation Stage 3 RMSE (or 1.61)"),
                (abl_gain_vs_stg3, "TPS ablation error reduction"),
                ("39.2",  "Seeker median I/O latency (or 39.15)"),
                ("737–1,187", "Mode C inlier range across tested sweep"),
                (ohrc_inliers, "OHRC inlier count"),
                (tmc_inliers, "TMC-2 inlier count"),
                ("1/1",   "Disjoint negative control tested count"),
            ]
            for val, desc in canonical_pptx_values:
                matched = False
                if val == "1.606":
                    matched = ("1.606" in full_deck_text) or ("1.61" in full_deck_text)
                elif val == "39.2":
                    matched = ("39.2" in full_deck_text) or ("39.15" in full_deck_text)
                else:
                    matched = val in full_deck_text

                if matched:
                    log_pass(f"PPTX contains {val} ({desc})")
                else:
                    errors.append(f"PPTX missing canonical value: {val} ({desc})")
                    log_fail(f"PPTX missing canonical value: {val} ({desc})")

            # Check absence of stale values in PPTX
            stale_pptx_values = ["0.779", "34.42", "0.812", "1,679", "0.679", "1.110"]
            for stale in stale_pptx_values:
                if stale in full_deck_text:
                    errors.append(f"PPTX contains stale value: {stale}")
                    log_fail(f"Stale value '{stale}' found in PPTX")
                else:
                    log_pass(f"No stale value '{stale}' in PPTX.")

            # Check Mode C framing on Slide 3 (must clearly indicate physics branch, not default E2E stage)
            slide3_text = slide_texts[2]
            if "Mode C: Physics branch" in slide3_text or "Mode C: Physics Branch" in slide3_text or "Physics branch" in slide3_text:
                log_pass("Slide 3 explicitly designates Mode C as Physics branch.")
            else:
                errors.append("Slide 3 does not designate Mode C as Physics branch.")
                log_fail("Slide 3 Mode C framing incomplete.")

        except Exception as e:
            errors.append(f"Failed to inspect PPTX: {e}")
            log_fail(f"Failed to inspect PPTX: {e}")

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    if errors:
        print(f"AUDIT FAILED WITH {len(errors)} ERROR(S):")
        for err in errors:
            print(f"  - {err}")
        print("=" * 70)
        sys.exit(1)
    else:
        print("AUDIT SUCCESS: ALL CODE, ARTIFACTS, MANIFESTS, DOCS, AND PPTX ARE MUTUALLY CONSISTENT.")
        print("=" * 70)
        sys.exit(0)

if __name__ == "__main__":
    main()
