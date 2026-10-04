"""
Seeker Latency Benchmark for massive Chandrayaan-2 push-broom line-scan arrays.
Benchmarks 500 random 1024x1024 window reads from an unindexed 1.12 GB OHRC binary raster.
"""
import time
import platform
from pathlib import Path
import numpy as np

from lunacorr.data.pyramid_reader import WindowedPyramidReader

def run_latency_benchmark():
    ohrc_xml = list(Path("data/ohrc/data/calibrated").glob("**/*_d_img_d18.xml"))[0]
    img_path = ohrc_xml.with_suffix(".img")
    reader = WindowedPyramidReader(img_path, lines=93686, samples=12000, itemsize=1, dtype=np.uint8)

    # Warmup 10 reads
    for _ in range(10):
        reader.read_window(1000, 2024, 1000, 2024)

    # Benchmark 500 random window seeks across 93,686 lines
    np.random.seed(42)
    rows = np.random.randint(0, 93686 - 1024, size=500)
    cols = np.random.randint(0, 12000 - 1024, size=500)

    times_ms = []
    for r, c in zip(rows, cols):
        t0 = time.perf_counter()
        w = reader.read_window(int(r), int(r + 1024), int(c), int(c + 1024))
        times_ms.append((time.perf_counter() - t0) * 1000.0)

    times_ms = np.array(times_ms)
    print("\n" + "=" * 65)
    print("WINDOWED PYRAMID SEEKER LATENCY BENCHMARK (N=500 RANDOM SEEKS)")
    print("=" * 65)
    print(f"Platform   : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"CPU        : {platform.processor()}")
    print(f"File Size  : {img_path.stat().st_size / (1024**3):.2f} GB ({img_path.name})")
    print(f"Window     : 1024 x 1024 pixels (1.05 MP)")
    print("-" * 65)
    print(f"Mean       : {np.mean(times_ms):.2f} ms")
    print(f"Median     : {np.median(times_ms):.2f} ms")
    print(f"P95        : {np.percentile(times_ms, 95):.2f} ms")
    print(f"Min / Max  : {np.min(times_ms):.2f} ms / {np.max(times_ms):.2f} ms")
    print("=" * 65)

    import json
    out_dir = Path("results")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "seeker_latency.json"
    result_data = {
        "experiment_id": "EXP-IO",
        "file_name": img_path.name,
        "file_size_gb": round(img_path.stat().st_size / (1024**3), 2),
        "window_size": "1024x1024",
        "n_samples": len(times_ms),
        "mean_latency_ms": round(float(np.mean(times_ms)), 2),
        "median_latency_ms": round(float(np.median(times_ms)), 2),
        "p95_latency_ms": round(float(np.percentile(times_ms, 95)), 2),
        "min_latency_ms": round(float(np.min(times_ms)), 2),
        "max_latency_ms": round(float(np.max(times_ms)), 2)
    }
    with open(out_file, "w") as f:
        json.dump(result_data, f, indent=2)
    print(f"Artifact saved: {out_file}")

if __name__ == "__main__":
    run_latency_benchmark()
