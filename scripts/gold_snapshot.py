import argparse, csv, datetime
from pathlib import Path
from utils_text import cosine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat", required=True)
    ap.add_argument("--vec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--similarity", type=float, default=0.95)
    args = ap.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    feats = {}
    vecs = {}
    with open(args.feat, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            feats[row["post_id"]] = row
    with open(args.vec, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            vecs[row["post_id"]] = [
                float(row[f"vector_{i}"]) for i in range(len(row) - 1)
            ]

    kept = []
    seen_vecs = []
    for pid, feat in feats.items():
        v = vecs[pid]
        if any(cosine(v, sv) >= args.similarity for sv in seen_vecs):
            continue
        seen_vecs.append(v)
        feat.update(
            {
                "snapshot_date": datetime.date.today().isoformat(),
                "model_name": "sa-demo",
                "split": "train",
            }
        )
        kept.append(feat)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(kept[0].keys()))
        w.writeheader()
        w.writerows(kept)
    print("Gold snapshot:", len(kept), "rows →", args.out)


if __name__ == "__main__":
    main()
