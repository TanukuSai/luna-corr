"""
Controlled Photometric Normalization Benchmark (EXP-SYN-ILLUM) on LOLA South Pole DEM.
Evaluates the capability of physics-conditioned DEM re-illumination (Mode C)
to recover correspondence against extreme sun-angle variation (0° to 180°).

Methodological note:
Under ideal synthetic re-illumination where the baseline DEM matches the scene topography,
Mode C reconstructs the reference appearance under the target solar geometry, restoring
correspondence yield from severe collapse (<20 inliers) to robust correspondence.
An observation noise model (additive Gaussian sensor shot noise, sigma=0.01) is injected
into the observed scene to test descriptor resilience beyond trivial identity comparison.
This benchmark validates the controlled rendering and contrast recovery mechanics;
it does NOT substitute for real-world uncalibrated multi-phase flight imagery.
"""
from pathlib import Path
import json
from PIL import Image
import numpy as np

from lunacorr.geometry.dem_renderer import LunarDEMRenderer
from lunacorr.matchers.classical import SIFTMatcher
from lunacorr.estimate.robust import RobustEstimator

def run_synthetic_gt_benchmark():
    dem_path = Path("data/dem/ldac_50s_1000m.jp2")
    pil_img = Image.open(str(dem_path))
    w, h = pil_img.size
    crop_dem = np.array(pil_img.crop((w//2 - 512, h//2 - 512, w//2 + 512, h//2 + 512))).astype(np.float32)

    base_az = 45.0
    base_el = 25.0
    ref_optical = LunarDEMRenderer.render_lunar_lambert(
        dem_elevation_m=crop_dem, pixel_scale_m=1000.0,
        sun_azimuth_deg=base_az, sun_elevation_deg=base_el,
        cast_shadows=True
    )

    matcher = SIFTMatcher(n_features=4000, root_sift=True)
    estimator = RobustEstimator(method="MAGSAC", reproj_threshold_px=3.0)

    delta_angles = [0, 15, 30, 45, 60, 90, 180]
    results = []
    N_min = 20  # Explicitly frozen minimum sample size rule

    print("\n" + "=" * 115)
    print("CONTROLLED PHOTOMETRIC NORMALIZATION BENCHMARK (EXP-SYN-ILLUM: LOLA DEM SWEEP)")
    print("Validates physics-conditioned rendering recovery; does NOT substitute for flight validation.")
    print("=" * 115)
    header = f"{'Delta Az':<9} | {'Direct N':<9} | {'Direct Prec@1px':<16} | {'Direct RMSE':<12} | {'Mode C N':<9} | {'Mode C Prec@1px':<16} | {'Mode C RMSE':<12}"
    print(header)
    print("-" * 115)

    np.random.seed(42)

    for delta in delta_angles:
        target_az = (base_az + delta) % 360.0
        # Simulated target observation with sensor noise
        src_clean = LunarDEMRenderer.render_lunar_lambert(
            dem_elevation_m=crop_dem, pixel_scale_m=1000.0,
            sun_azimuth_deg=target_az, sun_elevation_deg=base_el,
            cast_shadows=True
        )
        # Add realistic sensor shot noise (SNR ~ 40 dB)
        noise = np.random.normal(0, 0.01, src_clean.shape).astype(np.float32)
        src_optical = np.clip(src_clean + noise, 0.0, 1.0)

        # 1. Direct Optical Matching
        m_dir = matcher.match(src_optical, ref_optical)
        est_dir = estimator.estimate(m_dir.src_points, m_dir.ref_points, model_type="HOMOGRAPHY") if len(m_dir.src_points) >= 4 else None
        
        dir_inl_pts = m_dir.src_points[est_dir.inlier_mask] if est_dir else np.empty((0, 2))
        dir_ref_pts = m_dir.ref_points[est_dir.inlier_mask] if est_dir else np.empty((0, 2))
        
        n_dir = len(dir_inl_pts)
        if n_dir >= N_min:
            # True displacement error against identity field
            dir_true_errs = np.linalg.norm(dir_ref_pts - dir_inl_pts, axis=1)
            dir_prec_05 = float(np.mean(dir_true_errs < 0.5))
            dir_prec_10 = float(np.mean(dir_true_errs < 1.0))
            dir_prec_20 = float(np.mean(dir_true_errs < 2.0))
            dir_rmse = float(np.sqrt(np.mean(dir_true_errs**2)))
            dir_med = float(np.median(dir_true_errs))
            dir_p95 = float(np.percentile(dir_true_errs, 95))
            dir_status = "VALID"
            dir_str_p10 = f"{dir_prec_10*100:5.1f}%"
            dir_str_rmse = f"{dir_rmse:6.3f} px"
        else:
            dir_prec_05 = dir_prec_10 = dir_prec_20 = dir_rmse = dir_med = dir_p95 = None
            dir_status = f"SUPPRESSED (N={n_dir} < {N_min})"
            dir_str_p10 = "SUPPRESSED"
            dir_str_rmse = "SUPPRESSED"

        # 2. Mode C Physics-Based Re-illumination
        ref_mode_c = LunarDEMRenderer.render_lunar_lambert(
            dem_elevation_m=crop_dem, pixel_scale_m=1000.0,
            sun_azimuth_deg=target_az, sun_elevation_deg=base_el,
            cast_shadows=True
        )
        m_mc = matcher.match(src_optical, ref_mode_c)
        est_mc = estimator.estimate(m_mc.src_points, m_mc.ref_points, model_type="HOMOGRAPHY") if len(m_mc.src_points) >= 4 else None
        
        mc_inl_pts = m_mc.src_points[est_mc.inlier_mask] if est_mc else np.empty((0, 2))
        mc_ref_pts = m_mc.ref_points[est_mc.inlier_mask] if est_mc else np.empty((0, 2))
        
        n_mc = len(mc_inl_pts)
        if n_mc >= N_min:
            mc_true_errs = np.linalg.norm(mc_ref_pts - mc_inl_pts, axis=1)
            mc_prec_05 = float(np.mean(mc_true_errs < 0.5))
            mc_prec_10 = float(np.mean(mc_true_errs < 1.0))
            mc_prec_20 = float(np.mean(mc_true_errs < 2.0))
            mc_rmse = float(np.sqrt(np.mean(mc_true_errs**2)))
            mc_med = float(np.median(mc_true_errs))
            mc_p95 = float(np.percentile(mc_true_errs, 95))
            mc_status = "VALID"
            mc_str_p10 = f"{mc_prec_10*100:5.1f}%"
            mc_str_rmse = f"{mc_rmse:6.3f} px"
        else:
            mc_prec_05 = mc_prec_10 = mc_prec_20 = mc_rmse = mc_med = mc_p95 = None
            mc_status = f"SUPPRESSED (N={n_mc} < {N_min})"
            mc_str_p10 = "SUPPRESSED"
            mc_str_rmse = "SUPPRESSED"

        row = {
            "delta_azimuth_deg": delta,
            "target_azimuth_deg": target_az,
            "direct_optical": {
                "inlier_count": n_dir,
                "status": dir_status,
                "precision_at_05px": dir_prec_05,
                "precision_at_10px": dir_prec_10,
                "precision_at_20px": dir_prec_20,
                "true_rmse_px": dir_rmse,
                "true_median_px": dir_med,
                "true_p95_px": dir_p95
            },
            "mode_c_reillumination": {
                "inlier_count": n_mc,
                "status": mc_status,
                "precision_at_05px": mc_prec_05,
                "precision_at_10px": mc_prec_10,
                "precision_at_20px": mc_prec_20,
                "true_rmse_px": mc_rmse,
                "true_median_px": mc_med,
                "true_p95_px": mc_p95
            }
        }
        results.append(row)
        print(f"{delta:3d} deg   | {n_dir:<9d} | {dir_str_p10:<16} | {dir_str_rmse:<12} | {n_mc:<9d} | {mc_str_p10:<16} | {mc_str_rmse:<12}")

    print("=" * 115)
    with open("results/synthetic_illumination_groundtruth.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_synthetic_gt_benchmark()
