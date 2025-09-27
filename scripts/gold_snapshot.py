# scripts/gold_snapshot.py
import argparse, json, datetime, os
from pathlib import Path
import duckdb
import pyarrow as pa, pyarrow.parquet as pq
import numpy as np
from datasketch import MinHash, MinHashLSH
from utils_text import tokenize


def build_minhash(text, num_perm=64):
    mh = MinHash(num_perm=num_perm)
    for t in tokenize(text):
        mh.update(t.encode("utf-8"))
    return mh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--silver_dir", default="silver/cleaned_posts")
    ap.add_argument("--feat_dir", default="features/metadata")
    ap.add_argument("--vectors_npy", default="features/vectors.npy")
    ap.add_argument("--snapshot_root", default="gold/snapshots")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument(
        "--similarity", type=float, default=0.95
    )  # cosine threshold (post MinHash prefilter)
    args = ap.parse_args()

    # 1) Read cleaned + features with DuckDB (partition pushdown by date)
    con = duckdb.connect(database=":memory:")
    dt = args.date
    cleaned = con.execute(
        f"""
        SELECT * FROM read_parquet('{args.silver_dir}/dt={dt}/*/*/*.parquet', hive_partitioning=1)
    """
    ).arrow()  # pyarrow.Table

    features = con.execute(
        f"""
        SELECT * FROM read_parquet('{args.feat_dir}/dt={dt}/*/*/*.parquet', hive_partitioning=1)
    """
    ).arrow()

    # join by post_id (DuckDB – easier)
    con.register("cleaned", cleaned)
    con.register("features", features)
    joined = (
        con.execute(
            """
        SELECT c.post_id, c.lang, c.domain, c.clean_text, f.text_len, f.emoji_cnt, f.url_cnt
        FROM cleaned c JOIN features f USING (post_id)
    """
        )
        .arrow()
        .to_pylist()
    )

    if not joined:
        print("No rows for date:", dt)
        return

    # 2) MinHash LSH prefilter for near-dup suppression
    lsh = MinHashLSH(threshold=0.8, num_perm=64)
    kept_ids, kept_clean_text = [], []
    for row in joined:
        mh = build_minhash(row["clean_text"], num_perm=64)
        if lsh.query(mh):
            continue
        lsh.insert(row["post_id"], mh)
        kept_ids.append(row["post_id"])
        kept_clean_text.append(row["clean_text"])

    # 3) Optional cosine dedup on hashing vectors (for the kept_ids only)
    vec = np.load(args.vectors_npy)
    # build map post_id -> row_idx from index csv
    idx_map = {}
    with open("features/vector_index.csv", encoding="utf-8") as f:
        for line in f:
            rid, pid = line.strip().split(",")
            idx_map[pid] = int(rid)

    final_ids = []
    seen = []
    for pid in kept_ids:
        vi = idx_map.get(pid)
        if vi is None:
            continue
        v = vec[vi]  # already L2-normalized via hashing trick
        if any(float(np.dot(v, s)) >= args.similarity for s in seen):
            continue
        seen.append(v)
        final_ids.append(pid)

    # 4) Materialize final snapshot (immutable folder)
    snapshot_dir = Path(args.snapshot_root) / args.date
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # assemble final rows via DuckDB
    final_rows = (
        con.execute(
            f"""
        SELECT j.post_id, j.lang, j.domain, j.text_len, j.emoji_cnt, j.url_cnt
        FROM (SELECT * FROM (SELECT * FROM cleaned c JOIN features f USING (post_id))) j
        WHERE j.post_id IN ({','.join("'" + i + "'" for i in final_ids)})
    """
        )
        .arrow()
        .to_pylist()
    )

    # write Parquet
    pq.write_table(pa.Table.from_pylist(final_rows), snapshot_dir / "data.parquet")
    # manifest
    (snapshot_dir / "manifest.json").write_text(
        json.dumps(
            {
                "snapshot_date": args.date,
                "rows": len(final_rows),
                "model_name": "sa-demo",
                "strategy": {
                    "minhash_lsh": {"threshold": 0.8, "num_perm": 64},
                    "cosine_threshold": args.similarity,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    print("Gold snapshot written:", snapshot_dir)


if __name__ == "__main__":
    main()
