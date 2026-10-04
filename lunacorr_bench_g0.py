#!/usr/bin/env python3
"""
LUNA-CORR G0 benchmark (synthetic ground truth). Experiments E0-E1 style baselines.

WHAT THIS IS
  Takes real images (put lunar images in a folder), applies KNOWN transforms plus
  degradations, runs classical matchers, and measures error on held-out check points
  using the exact known transform. Each input image is one "scene"; confidence
  intervals are bootstrapped over scenes, not over matches.

WHAT THIS IS NOT
  Not Chandrayaan-2 validation. Brightness/blur/noise are NOT Sun-angle simulation.
  Results are G0 (synthetic) and must be labelled that way everywhere.

USAGE
  pip install opencv-python numpy scipy
  python lunacorr_bench_g0.py --images ./imgs --out ./results --pairs 20 --seed 0
"""
import argparse, csv, json, os, platform, sys, time
from pathlib import Path
import cv2, numpy as np

LEVELS = {  # difficulty bins: (max_rot_deg, scale_range, max_shift_frac, blur_sigma, noise_sigma, gamma_range)
    "L1": (10, (0.9, 1.1), 0.05, 0.0, 0.0, (1.0, 1.0)),
    "L2": (30, (0.7, 1.4), 0.10, 1.2, 4.0, (0.7, 1.4)),
    "L3": (60, (0.5, 2.0), 0.15, 2.0, 8.0, (0.5, 1.8)),
}

def load_gray(p):
    im = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if im is None: return None
    s = 1024 / max(im.shape)
    return cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else im

def make_pair(img, level, rng):
    rot, (s0, s1), sh, blur, noise, (g0, g1) = LEVELS[level]
    h, w = img.shape
    a = np.deg2rad(rng.uniform(-rot, rot)); s = np.exp(rng.uniform(np.log(s0), np.log(s1)))
    tx, ty = rng.uniform(-sh, sh) * w, rng.uniform(-sh, sh) * h
    c = np.array([w / 2, h / 2])
    R = s * np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    A = np.hstack([R, (c - R @ c + [tx, ty])[:, None]])          # source -> target (truth)
    tgt = cv2.warpAffine(img, A, (w, h), flags=cv2.INTER_CUBIC, borderValue=0)
    mask = cv2.warpAffine(np.full_like(img, 255), A, (w, h), flags=cv2.INTER_NEAREST)
    t = tgt.astype(np.float32) / 255
    t = t ** rng.uniform(g0, g1)
    if blur: t = cv2.GaussianBlur(t, (0, 0), blur)
    if noise: t = t + rng.normal(0, noise / 255, t.shape)
    return img, (np.clip(t, 0, 1) * 255).astype(np.uint8), A, mask > 0

def rootsift(d):
    d = d / (d.sum(1, keepdims=True) + 1e-7)
    return np.sqrt(d).astype(np.float32)

def detect(method, im):
    if method == "ORB":
        k, d = cv2.ORB_create(5000).detectAndCompute(im, None); return k, d, cv2.NORM_HAMMING
    k, d = cv2.SIFT_create(nfeatures=5000).detectAndCompute(im, None)
    if method == "RootSIFT" and d is not None: d = rootsift(d)
    return k, d, cv2.NORM_L2

def run_method(method, estimator, a, b):
    ka, da, norm = detect(method, a); kb, db, _ = detect(method, b)
    if da is None or db is None or len(ka) < 8 or len(kb) < 8: return None
    knn = cv2.BFMatcher(norm).knnMatch(da, db, k=2)
    good = [m for m, n in (p for p in knn if len(p) == 2) if m.distance < 0.8 * n.distance]
    if len(good) < 8: return None
    p = np.float32([ka[m.queryIdx].pt for m in good]); q = np.float32([kb[m.trainIdx].pt for m in good])
    flag = cv2.USAC_MAGSAC if estimator == "MAGSAC" else cv2.RANSAC
    H, inl = cv2.findHomography(p, q, flag, 3.0, maxIters=5000, confidence=0.999)
    if H is None: return None
    inl = inl.ravel().astype(bool)
    return H, p, inl, len(good)

def coverage(pts, shape, grid=8):
    if len(pts) == 0: return 0.0, 0.0
    h, w = shape
    ix = np.clip((pts[:, 0] / w * grid).astype(int), 0, grid - 1); iy = np.clip((pts[:, 1] / h * grid).astype(int), 0, grid - 1)
    cnt = np.bincount(iy * grid + ix, minlength=grid * grid).astype(float)
    pr = cnt[cnt > 0] / cnt.sum()
    return float((cnt > 0).mean()), float(-(pr * np.log(pr)).sum() / np.log(grid * grid))

def check_points(mask, shape, rng, n=100):
    ys, xs = np.nonzero(cv2.erode(mask.astype(np.uint8), np.ones((31, 31))))  # inside overlap, away from borders
    if len(xs) < n: return None
    return np.float32(np.c_[xs, ys][rng.choice(len(xs), n, replace=False)])  # target-frame points

def eval_pair(H, A, mask, shape, rng):
    pts_t = check_points(mask, shape, rng)
    if pts_t is None: return None
    Ainv = cv2.invertAffineTransform(A)
    src = (Ainv[:, :2] @ pts_t.T).T + Ainv[:, 2]                  # true source locations
    est = cv2.perspectiveTransform(src[None].astype(np.float32), H)[0]
    return np.linalg.norm(est - pts_t, axis=1)

def boot_ci(vals, rng, B=2000):
    v = np.asarray(vals, float)
    if len(v) < 3: return (float("nan"), float("nan"))
    m = [np.median(rng.choice(v, len(v))) for _ in range(B)]
    return tuple(np.percentile(m, [2.5, 97.5]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--pairs", type=int, default=20); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--success_px", type=float, default=3.0, help="PRE-REGISTER this before running; ours, not ISRO's")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in Path(a.images).iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"})
    scenes = [(p.name, load_gray(p)) for p in files]; scenes = [(n, i) for n, i in scenes if i is not None]
    if not scenes: sys.exit("no readable images")
    rng = np.random.default_rng(a.seed); rows = []
    methods = [("ORB", "RANSAC"), ("SIFT", "RANSAC"), ("RootSIFT", "RANSAC"), ("SIFT", "MAGSAC"), ("RootSIFT", "MAGSAC")]
    for name, img in scenes:
        for lv in LEVELS:
            for k in range(a.pairs):
                src, tgt, A, mask = make_pair(img, lv, rng)
                prng = np.random.default_rng(rng.integers(1 << 31))
                for m, est in methods:
                    t0 = time.time(); r = run_method(m, est, src, tgt); dt = time.time() - t0
                    row = dict(scene=name, level=lv, pair=k, method=m, estimator=est, runtime_s=round(dt, 3),
                               found=0, n_matches=0, n_inliers=0, inlier_ratio=np.nan, rmse=np.nan, median=np.nan, p95=np.nan,
                               occupied=np.nan, entropy=np.nan, success=0)
                    if r is not None:
                        H, p, inl, nm = r; e = eval_pair(H, A, mask, src.shape, prng)
                        if e is not None:
                            occ, ent = coverage(p[inl], src.shape)
                            row.update(found=1, n_matches=nm, n_inliers=int(inl.sum()), inlier_ratio=inl.mean(),
                                       rmse=float(np.sqrt((e ** 2).mean())), median=float(np.median(e)), p95=float(np.percentile(e, 95)),
                                       occupied=occ, entropy=ent, success=int(np.median(e) <= a.success_px))
                    rows.append(row)
        print(f"done {name}", flush=True)
    with open(out / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
    # summary: per (level, method, estimator); per-scene median first, then bootstrap over scenes
    summ = []; brng = np.random.default_rng(a.seed + 1)
    keys = sorted({(r["level"], r["method"], r["estimator"]) for r in rows})
    for lv, m, est in keys:
        sel = [r for r in rows if (r["level"], r["method"], r["estimator"]) == (lv, m, est)]
        per_scene = {}
        for r in sel: per_scene.setdefault(r["scene"], []).append(r)
        sc_med = [np.nanmedian([x["median"] for x in v]) for v in per_scene.values() if any(x["found"] for x in v)]
        lo, hi = boot_ci(sc_med, brng)
        summ.append(dict(level=lv, method=m, estimator=est, n_pairs=len(sel), n_scenes=len(per_scene),
                         success_rate=float(np.mean([x["success"] for x in sel])), found_rate=float(np.mean([x["found"] for x in sel])),
                         median_err_px=float(np.nanmedian([x["median"] for x in sel])) if sc_med else None,
                         scene_median_ci95=[float(lo), float(hi)], p95_err_px=float(np.nanpercentile([x["p95"] for x in sel], 50)) if sc_med else None,
                         inlier_ratio_med=float(np.nanmedian([x["inlier_ratio"] for x in sel])) if sc_med else None,
                         occupied_med=float(np.nanmedian([x["occupied"] for x in sel])) if sc_med else None,
                         runtime_med_s=float(np.median([x["runtime_s"] for x in sel]))))
    meta = dict(data_level="G0 synthetic (NOT Chandrayaan-2)", seed=a.seed, success_px=a.success_px, pairs_per_level=a.pairs,
                n_scenes=len(scenes), opencv=cv2.__version__, numpy=np.__version__, python=platform.python_version(),
                machine=platform.platform(), processor=platform.processor(), cpus=os.cpu_count(), levels=LEVELS)
    json.dump(dict(meta=meta, summary=summ), open(out / "summary.json", "w"), indent=1)
    with open(out / "summary.md", "w") as f:
        f.write("# G0 synthetic benchmark (not Chandrayaan-2 data)\n\n"
                f"Scenes: {len(scenes)}, pairs/level/scene: {a.pairs}, seed {a.seed}, success = median check-point error <= {a.success_px} px (ours).\n\n"
                "| level | method | estimator | success | found | median err px (scene CI95) | inlier ratio | occupied | s/pair |\n|---|---|---|---|---|---|---|---|---|\n")
        for s in summ:
            f.write(f"| {s['level']} | {s['method']} | {s['estimator']} | {s['success_rate']:.2f} | {s['found_rate']:.2f} | "
                    f"{s['median_err_px'] if s['median_err_px'] is None else round(s['median_err_px'],2)} "
                    f"({s['scene_median_ci95'][0]:.2f}-{s['scene_median_ci95'][1]:.2f}) | "
                    f"{'' if s['inlier_ratio_med'] is None else round(s['inlier_ratio_med'],2)} | "
                    f"{'' if s['occupied_med'] is None else round(s['occupied_med'],2)} | {s['runtime_med_s']:.2f} |\n")
    print("wrote", out)

if __name__ == "__main__":
    main()
