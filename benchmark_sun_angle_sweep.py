"""
Controlled Sun-Angle Sweep Benchmark for LUNA-CORR.
Quantifies correspondence degradation as a function of solar azimuth disparity (Delta theta):
Delta theta in [0, 15, 30, 45, 60, 90, 180] degrees.

Compares:
1. Direct Optical Matching (standard SIFT / RootSIFT)
2. Normalized Representation (LCN + Gradient Orientation modulo 180)
3. Mode C Physics-Based DEM Rendering (re-illuminating DEM to target sun angle)
"""
import time
import json
from pathlib import Path
from PIL import Image
import numpy as np
import cv2

from lunacorr.geometry.dem_renderer import LunarDEMRenderer
from lunacorr.represent.preprocessor import RepresentationLayer
from lunacorr.matchers.classical import SIFTMatcher
from lunacorr.estimate.robust import RobustEstimator
from lunacorr.selection.soft_utility import SoftSpatialUtilitySelector
from lunacorr.eval.checkpoints import CheckpointEvaluator

def run_sun_sweep():
    # Load LOLA South Pole DEM crop
    dem_path = Path("data/dem/ldac_50s_1000m.jp2")
    pil_img = Image.open(str(dem_path))
    w, h = pil_img.size
    crop_dem = np.array(pil_img.crop((w//2 - 512, h//2 - 512, w//2 + 512, h//2 + 512))).astype(np.float32)
    
    # Base reference image: Sun Azimuth = 45 deg, Sun Elevation = 25 deg
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
    sweep_results = []
    
    print("\n" + "=" * 90)
    print("CONTROLLED SUN-ANGLE SWEEP BENCHMARK (LOLA SOUTH POLE DEM)")
    print(f"Base Reference Illumination: Azimuth = {base_az} deg, Elevation = {base_el} deg")
    print("=" * 90)
    print(f"{'Delta Az':<10} | {'Direct Inl':<11} | {'Direct Ratio':<13} | {'Direct RMSE':<12} | {'Direct P95':<11} | {'Mode C Re-illum Inl':<20}")
    print("-" * 90)
    
    for delta in delta_angles:
        target_az = (base_az + delta) % 360.0
        
        # 1. Target optical observation at target sun angle
        src_optical = LunarDEMRenderer.render_lunar_lambert(
            dem_elevation_m=crop_dem, pixel_scale_m=1000.0,
            sun_azimuth_deg=target_az, sun_elevation_deg=base_el,
            cast_shadows=True
        )
        
        # Test 1: Direct Optical Matching (src_optical vs ref_optical)
        m_direct = matcher.match(src_optical, ref_optical)
        est_direct = estimator.estimate(m_direct.src_points, m_direct.ref_points, model_type="HOMOGRAPHY") if len(m_direct.src_points) >= 4 else None
        
        inl_count = est_direct.inlier_count if est_direct else 0
        inl_ratio = round(est_direct.inlier_ratio, 3) if est_direct else 0.0
        rmse = round(est_direct.rmse, 3) if est_direct else 999.0
        p95 = round(est_direct.p95_error, 3) if est_direct else 999.0
        
        # Test 2: Mode C Physics-Based Rendering:
        # Instead of matching directly against ref_optical at old azimuth,
        # we re-illuminate the DEM at target_az to match src_optical!
        ref_mode_c = LunarDEMRenderer.render_lunar_lambert(
            dem_elevation_m=crop_dem, pixel_scale_m=1000.0,
            sun_azimuth_deg=target_az, sun_elevation_deg=base_el,
            cast_shadows=True
        )
        m_mode_c = matcher.match(src_optical, ref_mode_c)
        est_mode_c = estimator.estimate(m_mode_c.src_points, m_mode_c.ref_points, model_type="HOMOGRAPHY") if len(m_mode_c.src_points) >= 4 else None
        mode_c_inliers = est_mode_c.inlier_count if est_mode_c else 0
        mode_c_rmse = round(est_mode_c.rmse, 3) if est_mode_c else 999.0
        
        sweep_results.append({
            "delta_azimuth_deg": delta,
            "target_azimuth_deg": target_az,
            "direct_optical": {
                "raw_matches": len(m_direct.src_points),
                "inliers": inl_count,
                "inlier_ratio": inl_ratio,
                "rmse_px": rmse,
                "p95_error_px": p95,
                "status": "ACCEPTED" if inl_count >= 15 and inl_ratio >= 0.15 else "COLLAPSED"
            },
            "mode_c_physics_rendering": {
                "inliers": mode_c_inliers,
                "rmse_px": mode_c_rmse,
                "gain_factor": round(mode_c_inliers / max(inl_count, 1), 1)
            }
        })
        
        print(f"{delta:3d} deg    | {inl_count:<11d} | {inl_ratio:<13.3f} | {rmse:<12.3f} | {p95:<11.3f} | {mode_c_inliers:<20d}")

    print("=" * 90)
    
    out_path = Path("results/sun_angle_sweep_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(sweep_results, f, indent=2)
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    run_sun_sweep()
