"""
Component Ablation Study for LUNA-CORR.
Measures metrics step-by-step across:
1. Raw SIFT (standard SIFT, L2 distance, ratio test=0.75, MAGSAC++)
2. + Local Contrast Normalization (LCN)
3. + RootSIFT (Hellinger kernel L1-sqrt)
4. + Soft Utility Selection (spatial quota + entropy)
5. + Adaptive TPS (Thin-Plate Spline deformation)

Evaluated on real Chandrayaan-2 TMC-2 stereo pair:
ch2_tmc_nra (Aft view) vs ch2_tmc_nrn (Nadir view).
"""
import time
import json
from pathlib import Path
import numpy as np
import cv2

from lunacorr.data.pds4_reader import PDS4Reader
from lunacorr.represent.preprocessor import RepresentationLayer
from lunacorr.matchers.classical import SIFTMatcher
from lunacorr.estimate.robust import RobustEstimator
from lunacorr.selection.soft_utility import SoftSpatialUtilitySelector
from lunacorr.estimate.nonrigid import ElasticTransformer
from lunacorr.eval.checkpoints import CheckpointEvaluator

def run_ablation():
    src_path = Path("data/tmc2/browse/raw/20260815/ch2_tmc_nra_20260815T2104543018_b_brw_d18.xml")
    ref_path = Path("data/tmc2/browse/raw/20260815/ch2_tmc_nrn_20260815T2104543018_b_brw_d18.xml")
    
    src_prod = PDS4Reader.load_product(src_path, max_dim=2048)
    ref_prod = PDS4Reader.load_product(ref_path, max_dim=2048)
    
    src_raw = src_prod.array
    ref_raw = ref_prod.array
    h, w = src_raw.shape[:2]
    
    # Preprocessor for LCN
    src_lcn = RepresentationLayer.local_contrast_normalization(src_raw, ksize=31)
    ref_lcn = RepresentationLayer.local_contrast_normalization(ref_raw, ksize=31)
    
    estimator = RobustEstimator(method="MAGSAC", reproj_threshold_px=3.0)
    
    results = []
    
    # -------------------------------------------------------------
    # Step 1: Raw SIFT (no LCN, no RootSIFT, no spatial selection, homography)
    # -------------------------------------------------------------
    t0 = time.time()
    sift_raw = cv2.SIFT_create(nfeatures=6000)
    u8_src = (np.clip(src_raw, 0, 1) * 255).astype(np.uint8)
    u8_ref = (np.clip(ref_raw, 0, 1) * 255).astype(np.uint8)
    
    kp1, des1 = sift_raw.detectAndCompute(u8_src, None)
    kp2, des2 = sift_raw.detectAndCompute(u8_ref, None)
    
    bf = cv2.BFMatcher(cv2.NORM_L2)
    matches = bf.knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.75 * n.distance]
    
    pts1 = np.float32([kp1[m.queryIdx].pt for m in good])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in good])
    pts1_raw, pts2_raw = pts1.copy(), pts2.copy()
    
    est1 = estimator.estimate(pts1, pts2, model_type="HOMOGRAPHY")
    inl_src1 = pts1[est1.inlier_mask]
    inl_ref1 = pts2[est1.inlier_mask]
    
    fit_s1, fit_r1, chk_s1, chk_r1 = CheckpointEvaluator.split_points(inl_src1, inl_ref1, np.ones(len(inl_src1)), 0.80, seed=42)
    def h1_trans(pts):
        pts_h = np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)])
        wh = (est1.matrix @ pts_h.T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    ev1 = CheckpointEvaluator.evaluate(fit_s1, fit_r1, chk_s1, chk_r1, h1_trans)
    
    results.append({
        "stage": "1. Raw SIFT",
        "description": "Standard SIFT + L2 distance + MAGSAC++ (no LCN, no RootSIFT, no quota)",
        "raw_matches": len(good),
        "inliers": int(est1.inlier_count),
        "inlier_ratio": round(est1.inlier_ratio, 3),
        "check_points_n": ev1.n_check_points,
        "check_rmse_px": round(ev1.check_rmse, 3),
        "check_median_px": round(ev1.check_median_px, 3),
        "check_p95_px": round(ev1.check_p95_px, 3),
        "runtime_s": round(time.time() - t0, 3)
    })
    
    # -------------------------------------------------------------
    # Step 2: + Local Contrast Normalization (LCN)
    # -------------------------------------------------------------
    t0 = time.time()
    u8_src_lcn = (np.clip(src_lcn, 0, 1) * 255).astype(np.uint8)
    u8_ref_lcn = (np.clip(ref_lcn, 0, 1) * 255).astype(np.uint8)
    
    kp1, des1 = sift_raw.detectAndCompute(u8_src_lcn, None)
    kp2, des2 = sift_raw.detectAndCompute(u8_ref_lcn, None)
    
    matches = bf.knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.75 * n.distance]
    
    pts1 = np.float32([kp1[m.queryIdx].pt for m in good])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in good])
    pts1_lcn, pts2_lcn = pts1.copy(), pts2.copy()
    
    est2 = estimator.estimate(pts1, pts2, model_type="HOMOGRAPHY")
    inl_src2 = pts1[est2.inlier_mask]
    inl_ref2 = pts2[est2.inlier_mask]
    
    fit_s2, fit_r2, chk_s2, chk_r2 = CheckpointEvaluator.split_points(inl_src2, inl_ref2, np.ones(len(inl_src2)), 0.80, seed=42)
    def h2_trans(pts):
        pts_h = np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)])
        wh = (est2.matrix @ pts_h.T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    ev2 = CheckpointEvaluator.evaluate(fit_s2, fit_r2, chk_s2, chk_r2, h2_trans)
    
    results.append({
        "stage": "2. + Local Contrast Norm",
        "description": "LCN (kernel=31) + standard SIFT + MAGSAC++",
        "raw_matches": len(good),
        "inliers": int(est2.inlier_count),
        "inlier_ratio": round(est2.inlier_ratio, 3),
        "check_points_n": ev2.n_check_points,
        "check_rmse_px": round(ev2.check_rmse, 3),
        "check_median_px": round(ev2.check_median_px, 3),
        "check_p95_px": round(ev2.check_p95_px, 3),
        "runtime_s": round(time.time() - t0, 3)
    })

    # -------------------------------------------------------------
    # Step 3: + RootSIFT (Hellinger kernel)
    # -------------------------------------------------------------
    t0 = time.time()
    matcher_rootsift = SIFTMatcher(n_features=6000, root_sift=True)
    m_root = matcher_rootsift.match(src_lcn, ref_lcn)
    
    est3 = estimator.estimate(m_root.src_points, m_root.ref_points, model_type="HOMOGRAPHY")
    inl_src3 = m_root.src_points[est3.inlier_mask]
    inl_ref3 = m_root.ref_points[est3.inlier_mask]
    inl_scores3 = m_root.scores[est3.inlier_mask]
    
    fit_s3, fit_r3, chk_s3, chk_r3 = CheckpointEvaluator.split_points(inl_src3, inl_ref3, inl_scores3, 0.80, seed=42)
    def h3_trans(pts):
        pts_h = np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)])
        wh = (est3.matrix @ pts_h.T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    ev3 = CheckpointEvaluator.evaluate(fit_s3, fit_r3, chk_s3, chk_r3, h3_trans)
    
    results.append({
        "stage": "3. + RootSIFT",
        "description": "LCN + RootSIFT (L1-sqrt) + MAGSAC++",
        "raw_matches": len(m_root.src_points),
        "inliers": int(est3.inlier_count),
        "inlier_ratio": round(est3.inlier_ratio, 3),
        "check_points_n": ev3.n_check_points,
        "check_rmse_px": round(ev3.check_rmse, 3),
        "check_median_px": round(ev3.check_median_px, 3),
        "check_p95_px": round(ev3.check_p95_px, 3),
        "runtime_s": round(time.time() - t0, 3)
    })

    # -------------------------------------------------------------
    # Step 4: + Soft Utility Selection (Spatial quota + residual penalty)
    # -------------------------------------------------------------
    t0 = time.time()
    selector = SoftSpatialUtilitySelector(grid_size=(8, 8), k_max_per_cell=15)
    uni4 = selector.select(inl_src3, inl_scores3, est3.residuals, src_raw.shape)
    
    sel_idx4 = uni4.selected_indices
    sel_src4 = inl_src3[sel_idx4]
    sel_ref4 = inl_ref3[sel_idx4]
    
    fit_s4, fit_r4, chk_s4, chk_r4 = CheckpointEvaluator.split_points(sel_src4, sel_ref4, inl_scores3[sel_idx4], 0.80, seed=42)
    def h4_trans(pts):
        pts_h = np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)])
        wh = (est3.matrix @ pts_h.T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    ev4 = CheckpointEvaluator.evaluate(fit_s4, fit_r4, chk_s4, chk_r4, h4_trans)
    
    results.append({
        "stage": "4. + Soft Utility Selection",
        "description": "LCN + RootSIFT + Soft Utility (8x8 grid quotas, residual penalty)",
        "raw_matches": len(m_root.src_points),
        "inliers": len(sel_src4),
        "inlier_ratio": round(est3.inlier_ratio, 3),
        "check_points_n": ev4.n_check_points,
        "check_rmse_px": round(ev4.check_rmse, 3),
        "check_median_px": round(ev4.check_median_px, 3),
        "check_p95_px": round(ev4.check_p95_px, 3),
        "runtime_s": round(time.time() - t0, 3)
    })

    # -------------------------------------------------------------
    # Step 5: + Adaptive TPS (Non-Rigid Elastic Spline)
    # -------------------------------------------------------------
    t0 = time.time()
    elastic = ElasticTransformer(smoothing=0.5)
    tps_res = elastic.fit(fit_s4, fit_r4)
    def tps_trans(pts):
        return pts + tps_res.rbf_model(pts)
    ev5 = CheckpointEvaluator.evaluate(fit_s4, fit_r4, chk_s4, chk_r4, tps_trans)
    
    results.append({
        "stage": "5. + Adaptive TPS",
        "description": "LCN + RootSIFT + Soft Utility + Thin-Plate Spline Elastic Warping",
        "raw_matches": len(m_root.src_points),
        "inliers": len(sel_src4),
        "inlier_ratio": round(est3.inlier_ratio, 3),
        "check_points_n": ev5.n_check_points,
        "check_rmse_px": round(ev5.check_rmse, 3),
        "check_median_px": round(ev5.check_median_px, 3),
        "check_p95_px": round(ev5.check_p95_px, 3),
        "runtime_s": round(time.time() - t0, 3)
    })

    # -------------------------------------------------------------
    # FIXED EVALUATION SET ABLATION (Apples-to-Apples, N=150 Frozen)
    # -------------------------------------------------------------
    matcher_master = SIFTMatcher(n_features=6000, root_sift=True)
    m_master = matcher_master.match(src_lcn, ref_lcn)
    est_master = estimator.estimate(m_master.src_points, m_master.ref_points, model_type="HOMOGRAPHY")
    inl_master_s = m_master.src_points[est_master.inlier_mask]
    inl_master_r = m_master.ref_points[est_master.inlier_mask]

    np.random.seed(42)
    perm = np.random.permutation(len(inl_master_s))
    n_test = 150
    test_idx = perm[:n_test]
    train_idx = perm[n_test:]

    fixed_eval_s = inl_master_s[test_idx]
    fixed_eval_r = inl_master_r[test_idx]

    train_s = inl_master_s[train_idx]
    train_r = inl_master_r[train_idx]

    # Helper to strictly filter out any training candidate within 3px of the withheld test set
    def filter_disjoint_training(cand_s, cand_r, test_s, min_dist=3.0):
        if len(cand_s) == 0:
            return cand_s, cand_r
        diff = cand_s[:, np.newaxis, :] - test_s[np.newaxis, :, :]
        dists = np.linalg.norm(diff, axis=2)
        min_dists = np.min(dists, axis=1)
        disjoint_mask = min_dists > min_dist
        return cand_s[disjoint_mask], cand_r[disjoint_mask]

    def measure_fixed(trans_func):
        pred = trans_func(fixed_eval_s)
        errs = np.linalg.norm(fixed_eval_r - pred, axis=1)
        return {
            "fixed_n": len(errs),
            "fixed_rmse_px": round(float(np.sqrt(np.mean(errs**2))), 3),
            "fixed_median_px": round(float(np.median(errs)), 3),
            "fixed_p95_px": round(float(np.percentile(errs, 95)), 3)
        }

    # Fixed metric 1: Raw SIFT (fit on disjoint candidates)
    f_s1, f_r1 = filter_disjoint_training(pts1_raw, pts2_raw, fixed_eval_s, min_dist=3.0)
    est1_f = estimator.estimate(f_s1, f_r1, model_type="HOMOGRAPHY")
    def h1_fixed(pts):
        wh = (est1_f.matrix @ np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)]).T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    results[0]["fixed_eval_set"] = measure_fixed(h1_fixed)

    # Fixed metric 2: + LCN (fit on disjoint candidates)
    f_s2, f_r2 = filter_disjoint_training(pts1_lcn, pts2_lcn, fixed_eval_s, min_dist=3.0)
    est2_f = estimator.estimate(f_s2, f_r2, model_type="HOMOGRAPHY")
    def h2_fixed(pts):
        wh = (est2_f.matrix @ np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)]).T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    results[1]["fixed_eval_set"] = measure_fixed(h2_fixed)

    # Fixed metric 3: + RootSIFT (fit on disjoint consensus pool)
    train_s_purged, train_r_purged = filter_disjoint_training(train_s, train_r, fixed_eval_s, min_dist=3.0)
    est3_f = estimator.estimate(train_s_purged, train_r_purged, model_type="HOMOGRAPHY")
    def h3_fixed(pts):
        wh = (est3_f.matrix @ np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)]).T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    results[2]["fixed_eval_set"] = measure_fixed(h3_fixed)

    # Fixed metric 4: + Soft Utility (selected strictly from purged consensus inliers)
    train_s_inl = train_s_purged[est3_f.inlier_mask]
    train_r_inl = train_r_purged[est3_f.inlier_mask]
    selector_f = SoftSpatialUtilitySelector(grid_size=(8, 8), k_max_per_cell=15)
    uni4_f = selector_f.select(train_s_inl, np.ones(len(train_s_inl)), est3_f.residuals, src_raw.shape)
    sel_s_f = train_s_inl[uni4_f.selected_indices]
    sel_r_f = train_r_inl[uni4_f.selected_indices]
    est4_f = estimator.estimate(sel_s_f, sel_r_f, model_type="HOMOGRAPHY")
    def h4_fixed(pts):
        wh = (est4_f.matrix @ np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)]).T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    results[3]["fixed_eval_set"] = measure_fixed(h4_fixed)

    # Fixed metric 5: + Adaptive TPS (fitted on purged, spatially uniform tie points)
    elastic_f = ElasticTransformer(smoothing=0.5)
    tps_res_f = elastic_f.fit(sel_s_f, sel_r_f)
    def tps_fixed(pts):
        return pts + tps_res_f.rbf_model(pts)
    results[4]["fixed_eval_set"] = measure_fixed(tps_fixed)

    out_file = Path("results/ablation_study_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n" + "=" * 95)
    print("LUNA-CORR COMPONENT ABLATION STUDY: FIXED EVALUATION SET (N=150 FROZEN POINTS)")
    print("=" * 95)
    header = f"{'Stage':<28} | {'Fixed N':<8} | {'Fixed RMSE':<11} | {'Fixed Med':<10} | {'Fixed P95':<10}"
    print(header)
    print("-" * 95)
    for r in results:
        fe = r["fixed_eval_set"]
        print(f"{r['stage']:<28} | {fe['fixed_n']:<8} | {fe['fixed_rmse_px']:<11.3f} | {fe['fixed_median_px']:<10.3f} | {fe['fixed_p95_px']:<10.3f}")
    print("=" * 95)

if __name__ == "__main__":
    run_ablation()
