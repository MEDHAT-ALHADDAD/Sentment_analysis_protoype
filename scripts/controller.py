import subprocess, argparse, sys, os
from pathlib import Path


def run(cmd):
    print(">>", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/sample_posts.jsonl")
    ap.add_argument("--dim", type=int, default=64)
    args = ap.parse_args()

    Path("bronze").mkdir(exist_ok=True)
    Path("silver").mkdir(exist_ok=True)
    Path("features").mkdir(exist_ok=True)
    Path("gold").mkdir(exist_ok=True)
    Path("serving").mkdir(exist_ok=True)

    run(
        [
            sys.executable,
            "scripts/bronze_ingest.py",
            "--input",
            args.input,
            "--out",
            "bronze",
        ]
    )
    run(
        [
            sys.executable,
            "scripts/silver_clean.py",
            "--input",
            args.input,
            "--out",
            "silver/cleaned_posts.csv",
        ]
    )
    run(
        [
            sys.executable,
            "scripts/silver_features.py",
            "--clean",
            "silver/cleaned_posts.csv",
            "--feat",
            "features/features.csv",
            "--vec",
            "features/vectors.csv",
            "--dim",
            str(args.dim),
        ]
    )
    run(
        [
            sys.executable,
            "scripts/gold_snapshot.py",
            "--feat",
            "features/features.csv",
            "--vec",
            "features/vectors.csv",
            "--out",
            "gold/training_snapshot.csv",
        ]
    )


if __name__ == "__main__":
    main()
