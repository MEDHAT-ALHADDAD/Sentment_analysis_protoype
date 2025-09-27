import argparse, json, shutil
from pathlib import Path
from datetime import date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"raw_{date.today().isoformat()}.jsonl"
    shutil.copy(args.input, out)
    print("Bronze archive:", out)


if __name__ == "__main__":
    main()
