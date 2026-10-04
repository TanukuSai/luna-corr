"""
Test that validates benchmark cross-consistency across manifests, artifacts, and documentation.
"""
import sys
from pathlib import Path

def test_benchmark_cross_consistency():
    root = Path(__file__).resolve().parent.parent
    tools_dir = root / "tools"
    sys.path.insert(0, str(tools_dir))
    import validate_benchmark_consistency
    # Must run main() without raising SystemExit(1)
    try:
        validate_benchmark_consistency.main()
    except SystemExit as e:
        assert e.code == 0, f"Benchmark consistency check failed with exit code {e.code}"
