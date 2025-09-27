# scripts/silver_features.py
import argparse, json, time, csv
from pathlib import Path
from utils_text import tokenize, hashing_vector
from metrics import incr, setval
import pyarrow as pa, pyarrow.parquet as pq
import numpy as np
from rapidfuzz.string_metric import jaro_winkler_similarity


def write_features_parquet(rows, base_dir, created_at, source, lang):
    if not rows:
        return
    dt = (created_at or "")[:10]
    table = pa.Table.from_pylist(rows)
    out_dir = (
        Path(base_dir)
        / f"dt={dt}"
        / f"source={source or 'unknown'}"
        / f"lang={lang or 'xx'}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out_dir / f"part-{int(time.time()*1000)}.parquet")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean_topic", default="topics/social.clean.jsonl")
    ap.add_argument("--feat_dir", default="features/metadata")
    ap.add_argument("--vectors_npy", default="features/vectors.npy")
    ap.add_argument("--vector_index", default="features/vector_index.csv")
    ap.add_argument("--dim", type=int, default=128)
    ap.add_argument("--poll", type=float, default=1.0)
    args = ap.parse_args()

    Path(args.feat_dir).mkdir(parents=True, exist_ok=True)
    Path(args.vector_index).parent.mkdir(parents=True, exist_ok=True)

    offset_file = Path(args.clean_topic + ".offset.features")
    last = int(offset_file.read_text()) if offset_file.exists() else 0

    # vectors in memory → append to .npy periodically
    vec_rows, vec_post_ids = [], []

    # features parquet buffer
    feat_batch = []

    while True:
        lines = Path(args.clean_topic).read_text(encoding="utf-8").splitlines()
        new = lines[last:]
        if not new:
            time.sleep(args.poll)
            continue

        for line in new:
            row = json.loads(line)
            # (optional) super-quick text near-dup prefilter on clean_text
            # if jaro_winkler ~ 1.0 to any recent text, you might skip vectorizing (demo only)
            # (We keep all to avoid dropping tiny dataset items.)

            feat = {
                "post_id": row["post_id"],
                "lang": row["lang"],
                "domain": row["domain"],
                "hour_of_day": row["created_at"][11:13] if row["created_at"] else "",
                "text_len": row["text_len"],
                "emoji_cnt": row["emoji_cnt"],
                "url_cnt": row["url_cnt"],
            }
            feat_batch.append(feat)

            vec = hashing_vector(tokenize(row["clean_text"]), dim=args.dim)
            vec_rows.append(vec)
            vec_post_ids.append(row["post_id"])

            incr("silver_features", "rows", 1)
            print("Features+Vector:", row["post_id"])

            if len(feat_batch) >= 50:
                write_features_parquet(
                    feat_batch,
                    args.feat_dir,
                    row["created_at"],
                    row["source"],
                    row["lang"],
                )
                feat_batch.clear()

        last += len(new)
        offset_file.write_text(str(last))
        setval("silver_features", "offset", last)

        # flush features parquet
        if feat_batch:
            last_row = json.loads(new[-1])
            write_features_parquet(
                feat_batch,
                args.feat_dir,
                last_row["created_at"],
                last_row["source"],
                last_row["lang"],
            )
            feat_batch.clear()

        # append vectors to .npy + index
        if vec_rows:
            # append or create
            npy = Path(args.vectors_npy)
            arr = np.array(vec_rows, dtype="float32")
            if npy.exists():
                old = np.load(npy)
                arr = np.vstack([old, arr])
            np.save(npy, arr)
            with open(args.vector_index, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                start = (arr.shape[0] - len(vec_rows)) if npy.exists() else 0
                for i, pid in enumerate(vec_post_ids):
                    w.writerow([start + i, pid])
            vec_rows.clear()
            vec_post_ids.clear()
            setval("silver_features", "vectors_count", int(arr.shape[0]))
