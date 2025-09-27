import argparse, json, datetime
from pathlib import Path
from utils_text import cosine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat", default="features/features.jsonl")
    ap.add_argument("--vec", default="features/vectors.jsonl")
    ap.add_argument("--outdir", default="gold")
    ap.add_argument("--similarity", type=float, default=0.95)
    args = ap.parse_args()

    Path(args.outdir).mkdir(exist_ok=True)

    feats = {}
    with open(args.feat, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            feats[row["post_id"]] = row

    vecs = {}
    with open(args.vec, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vecs[row["post_id"]] = row["vector"]

    kept, seen_vecs = [], []
    for pid, feat in feats.items():
        v = vecs.get(pid)
        if not v:
            continue
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

    out = (
        Path(args.outdir)
        / f"training_snapshot_{datetime.date.today().isoformat()}.jsonl"
    )
    with open(out, "w", encoding="utf-8") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("Gold snapshot created:", out, "rows:", len(kept))


if __name__ == "__main__":
    main()
