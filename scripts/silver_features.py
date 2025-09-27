import argparse, csv
from pathlib import Path
from utils_text import tokenize, hashing_vector


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", required=True)
    ap.add_argument("--feat", required=True)
    ap.add_argument("--vec", required=True)
    ap.add_argument("--dim", type=int, default=64)
    args = ap.parse_args()
    Path(args.feat).parent.mkdir(parents=True, exist_ok=True)

    feats = []
    vecs = []
    with open(args.clean, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            text = row["clean_text"]
            feats.append(
                {
                    "post_id": row["post_id"],
                    "lang": row["lang"],
                    "domain": row["domain"],
                    "hour_of_day": row["created_at"][11:13],
                    "text_len": row["text_len"],
                    "emoji_cnt": row["emoji_cnt"],
                    "url_cnt": row["url_cnt"],
                }
            )
            vec = hashing_vector(tokenize(text), dim=args.dim)
            vecs.append(
                {
                    "post_id": row["post_id"],
                    **{f"vector_{i}": vec[i] for i in range(args.dim)},
                }
            )

    with open(args.feat, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(feats[0].keys()))
        w.writeheader()
        w.writerows(feats)
    with open(args.vec, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(vecs[0].keys()))
        w.writeheader()
        w.writerows(vecs)

    print("Silver features:", len(feats), "rows")


if __name__ == "__main__":
    main()
