"""
Command-line interface for LUNA-CORR.
"""
import argparse
from pathlib import Path
import sys

from .pipeline.inference import LunarRegistrationPipeline
from .train.trainer import LunarTrainer

def main():
    parser = argparse.ArgumentParser(
        prog="lunacorr",
        description="LUNA-CORR: Multi-modal, Sun-angle and scale invariant image correspondence (SIH 2026 PS 26166)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: register
    reg_parser = subparsers.add_parser("register", help="Register a source image to a reference image")
    reg_parser.add_argument("--source", "-s", required=True, type=Path, help="Path to source image (.xml or image file)")
    reg_parser.add_argument("--reference", "-r", required=True, type=Path, help="Path to reference image (.xml or image file)")
    reg_parser.add_argument("--out", "-o", default=Path("results/run_latest"), type=Path, help="Output directory")
    reg_parser.add_argument("--method", default="RootSIFT", choices=["RootSIFT", "SIFT"], help="Feature matcher method")

    # Command: train
    train_parser = subparsers.add_parser("train", help="Train / fine-tune correspondence network")
    train_parser.add_argument("--data-dir", "-d", required=True, type=Path, help="Directory containing lunar training images")
    train_parser.add_argument("--epochs", "-e", default=5, type=int, help="Number of training epochs")
    train_parser.add_argument("--batch-size", "-b", default=4, type=int, help="Batch size")
    train_parser.add_argument("--out", "-o", default=Path("models/checkpoints"), type=Path, help="Model output directory")

    args = parser.parse_args()

    if args.command == "register":
        pipeline = LunarRegistrationPipeline()
        print(f"\n[LUNA-CORR] Registering:")
        print(f"  Source   : {args.source}")
        print(f"  Reference: {args.reference}")
        print(f"  Output   : {args.out}\n")

        res = pipeline.run(args.source, args.reference, output_dir=args.out)

        print("-" * 50)
        print(f"Status           : {res.decision.status}")
        print(f"Inliers Found    : {len(res.match_points)}")
        if res.decision.accepted:
            print(f"Occupied Ratio   : {res.decision.metrics.get('occupied_ratio', 0):.2f}")
            print(f"Spatial Entropy  : {res.decision.metrics.get('entropy', 0):.2f}")
            print(f"P95 Error (px)   : {res.decision.metrics.get('p95_residual_px', 0):.2f}")
            print(f"Confidence Score : {res.decision.confidence_score:.3f}")
            print(f"Deliverables     : Saved to {args.out}")
        else:
            print(f"Abstain Reasons  : {', '.join(res.decision.reason_codes)}")
        print("-" * 50)

    elif args.command == "train":
        trainer = LunarTrainer()
        # Find images in data-dir
        exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
        images = [p for p in args.data_dir.rglob("*") if p.suffix.lower() in exts]
        if not images:
            sys.exit(f"Error: No images found in {args.data_dir}")

        trainer.fit(image_paths=images, epochs=args.epochs, batch_size=args.batch_size, output_dir=args.out)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
