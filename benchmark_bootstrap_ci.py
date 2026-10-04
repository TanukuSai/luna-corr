"""
Computes non-parametric bootstrap 95% confidence intervals (B=1000)
for the Fixed Evaluation Set Ablation (N=150 frozen points).
"""
from pathlib import Path
import json
import numpy as np
import cv2

from lunacorr.data.pds4_reader import PDS4Reader
from lunacorr.represent.preprocessor import RepresentationLayer
from lunacorr.matchers.classical import SIFTMatcher
from lunacorr.estimate.robust import RobustEstimator
from lunacorr.selection.soft_utility import SoftSpatialUtilitySelector
from lunacorr.estimate.nonrigid import ElasticTransformer

def run_bootstrap_ablation():
    src_path = Path("data/tmc2/browse/raw/20260815/ch2_tmc_nra_20260815T2104543018_b_brw_d18.xml")
    ref_path = Path("data/tmc2/browse/raw/20260815/ch2_tmc_nrn_20260815T2104543018_b_brw_d18.xml")

    src_prod = PDS4Reader.load_product(src_path, max_dim=2048)
    ref_prod = PDS4Reader.load_product(ref_path, max_dim=2048)

    src_raw, ref_raw = src_prod.array, ref_prod.array
    src_lcn = RepresentationLayer.local_contrast_normalization(src_raw, ksize=31)
    ref_lcn = RepresentationLayer.local_contrast_normalization(ref_raw, ksize=31)

    estimator = RobustEstimator(method="MAGSAC", reproj_threshold_px=3.0)

    # Master fixed evaluation set of 150 consensus held-out points
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

    def get_bootstrap_ci(errors, n_boot=1000, ci=95):
        np.random.seed(42)
        n = len(errors)
        boot_rmse, boot_med, boot_p95 = [], [], []
        for _ in range(n_boot):
            sample = np.random.choice(errors, size=n, replace=True)
            boot_rmse.append(np.sqrt(np.mean(sample**2)))
            boot_med.append(np.median(sample))
            boot_p95.append(np.percentile(sample, 95))
        alpha = (100 - ci) / 2.0
        return {
            "rmse": (round(float(np.sqrt(np.mean(errors**2))), 3),
                     round(float(np.percentile(boot_rmse, alpha)), 3),
                     round(float(np.percentile(boot_rmse, 100 - alpha)), 3)),
            "median": (round(float(np.median(errors)), 3),
                       round(float(np.percentile(boot_med, alpha)), 3),
                       round(float(np.percentile(boot_med, 100 - alpha)), 3)),
            "p95": (round(float(np.percentile(errors, 95)), 3),
                    round(float(np.percentile(boot_p95, alpha)), 3),
                    round(float(np.percentile(boot_p95, 100 - alpha)), 3))
        }

    # 1. Raw SIFT
    sift_raw = cv2.SIFT_create(nfeatures=6000)
    u8_src = (np.clip(src_raw, 0, 1) * 255).astype(np.uint8)
    u8_ref = (np.clip(ref_raw, 0, 1) * 255).astype(np.uint8)
    kp1, des1 = sift_raw.detectAndCompute(u8_src, None)
    kp2, des2 = sift_raw.detectAndCompute(u8_ref, None)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    m_raw = bf.knnMatch(des1, des2, k=2)
    good_raw = [m for m, n in m_raw if m.distance < 0.75 * n.distance]
    pts1 = np.float32([kp1[m.queryIdx].pt for m in good_raw])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in good_raw])
    est1 = estimator.estimate(pts1, pts2, model_type="HOMOGRAPHY")
    def h1(pts):
        wh = (est1.matrix @ np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)]).T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    errs1 = np.linalg.norm(fixed_eval_r - h1(fixed_eval_s), axis=1)

    # 2. + LCN
    u8_src_lcn = (np.clip(src_lcn, 0, 1) * 255).astype(np.uint8)
    u8_ref_lcn = (np.clip(ref_lcn, 0, 1) * 255).astype(np.uint8)
    kp1, des1 = sift_raw.detectAndCompute(u8_src_lcn, None)
    kp2, des2 = sift_raw.detectAndCompute(u8_ref_lcn, None)
    m_lcn = bf.knnMatch(des1, des2, k=2)
    good_lcn = [m for m, n in m_lcn if m.distance < 0.75 * n.distance]
    pts1 = np.float32([kp1[m.queryIdx].pt for m in good_lcn])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in good_lcn])
    est2 = estimator.estimate(pts1, pts2, model_type="HOMOGRAPHY")
    def h2(pts):
        wh = (est2.matrix @ np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)]).T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    errs2 = np.linalg.norm(fixed_eval_r - h2(fixed_eval_s), axis=1)

    # 3. + RootSIFT
    est3 = estimator.estimate(train_s, train_r, model_type="HOMOGRAPHY")
    def h3(pts):
        wh = (est3.matrix @ np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)]).T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    errs3 = np.linalg.norm(fixed_eval_r - h3(fixed_eval_s), axis=1)

    # 4. + Soft Utility
    train_s_inl = train_s[est3.inlier_mask]
    train_r_inl = train_r[est3.inlier_mask]
    selector = SoftSpatialUtilitySelector(grid_size=(8, 8), k_max_per_cell=15)
    uni4 = selector.select(train_s_inl, np.ones(len(train_s_inl)), est3.residuals, src_raw.shape)
    sel_s = train_s_inl[uni4.selected_indices]
    sel_r = train_r_inl[uni4.selected_indices]
    est4 = estimator.estimate(sel_s, sel_r, model_type="HOMOGRAPHY")
    def h4(pts):
        wh = (est4.matrix @ np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)]).T).T
        return wh[:, :2] / (wh[:, 2:3] + 1e-9)
    errs4 = np.linalg.norm(fixed_eval_r - h4(fixed_eval_s), axis=1)

    # 5. + Adaptive TPS
    elastic = ElasticTransformer(smoothing=0.5)
    tps_res = elastic.fit(sel_s, sel_r)
    def tps_trans(pts):
        return pts + tps_res.rbf_model(pts)
    errs5 = np.linalg.norm(fixed_eval_r - tps_trans(fixed_eval_s), axis=1)

    stages = [
        ("1. Raw SIFT", errs1),
        ("2. + Local Contrast Norm", errs2),
        ("3. + RootSIFT", errs3),
        ("4. + Soft Utility", errs4),
        ("5. + Adaptive TPS", errs5)
    ]

    out_data = {}
    print("\n" + "=" * 105)
    print("FIXED EVALUATION SET ABLATION WITH 95% BOOTSTRAP CONFIDENCE INTERVALS (B=1000)")
    print("=" * 105)
    print(f"{'Stage':<26} | {'RMSE [95% CI] (px)':<24} | {'Median [95% CI] (px)':<24} | {'P95 [95% CI] (px)':<24}")
    print("-" * 105)
    for name, errs in stages:
        ci_res = get_bootstrap_ci(errs)
        out_data[name] = ci_res
        r_pt, r_l, r_u = ci_res['rmse']
        m_pt, m_l, m_u = ci_res['median']
        p_pt, p_l, p_u = ci_res['p95']
        print(f"{name:<26} | {r_pt:.3f} [{r_l:.3f}, {r_u:.3f}]      | {m_pt:.3f} [{m_l:.3f}, {m_u:.3f}]      | {p_pt:.3f} [{p_l:.3f}, {p_u:.3f}]")
    print("=" * 105)

    with open("results/ablation_bootstrap_ci.json", "w") as f:
        json.dump(out_data, f, indent=2)

if __name__ == "__main__":
    run_bootstrap_ablation()
