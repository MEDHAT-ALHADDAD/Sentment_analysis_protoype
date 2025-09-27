# scripts/silver_clean.py
import argparse, json, time, hashlib, datetime
from pathlib import Path
from utils_text import clean_text, lang_detect
from metrics import incr, setval
import pyarrow as pa
import pyarrow.parquet as pq


def write_parquet_partition(rows, base_dir, created_at, source, lang):
    if not rows:
        return
    dt = (created_at or "")[:10] or datetime.date.today().isoformat()
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
    ap.add_argument("--raw", default="topics/social.raw.jsonl")
    ap.add_argument("--clean_topic", default="topics/social.clean.jsonl")
    ap.add_argument("--dlq_topic", default="topics/social.dlq.jsonl")
    ap.add_argument("--silver_dir", default="silver/cleaned_posts")
    ap.add_argument("--poll", type=float, default=1.0)
    args = ap.parse_args()

    Path(args.clean_topic).parent.mkdir(parents=True, exist_ok=True)
    Path(args.dlq_topic).parent.mkdir(parents=True, exist_ok=True)
    Path(args.silver_dir).mkdir(parents=True, exist_ok=True)

    offset_file = Path(args.raw + ".offset")
    last = int(offset_file.read_text()) if offset_file.exists() else 0

    # buffer for Parquet micro-batches
    batch = []

    while True:
        lines = Path(args.raw).read_text(encoding="utf-8").splitlines()
        new = lines[last:]
        if not new:
            time.sleep(args.poll)
            continue

        with open(args.clean_topic, "a", encoding="utf-8") as f_clean, open(
            args.dlq_topic, "a", encoding="utf-8"
        ) as f_dlq:
            for raw_line in new:
                try:
                    rec = json.loads(raw_line)
                    # assertions: required fields
                    for req in ("post_id", "text", "created_at", "source", "domain"):
                        if req not in rec or not rec[req]:
                            raise ValueError(f"missing_field:{req}")

                    clean, pii, emoji_cnt, url_cnt, _ = clean_text(rec["text"])
                    if not clean:
                        raise ValueError("empty_clean_text")

                    lang = lang_detect(clean, rec.get("lang_hint"))
                    out = {
                        "post_id": rec["post_id"],
                        "source": rec.get("source", ""),
                        "domain": rec.get("domain", ""),
                        "created_at": rec.get("created_at", ""),
                        "lang": lang,
                        "clean_text": clean,
                        "record_hash": hashlib.sha256(
                            (clean + rec.get("source", "")).encode()
                        ).hexdigest()[:16],
                        "pii_found": int(pii),
                        "emoji_cnt": emoji_cnt,
                        "url_cnt": url_cnt,
                        "text_len": len(clean),
                    }
                    f_clean.write(json.dumps(out, ensure_ascii=False) + "\n")
                    batch.append(out)
                    incr("silver_clean", "cleaned", 1)
                    print("Cleaned:", out["post_id"])

                    # micro-batch Parquet write when buffer grows
                    if len(batch) >= 50:
                        write_parquet_partition(
                            batch,
                            args.silver_dir,
                            out["created_at"],
                            out["source"],
                            out["lang"],
                        )
                        batch.clear()

                except Exception as e:
                    err = {"error": str(e), "raw": raw_line}
                    f_dlq.write(json.dumps(err, ensure_ascii=False) + "\n")
                    incr("silver_clean", "dlq", 1)
                    print("DLQ:", err["error"])

        last += len(new)
        offset_file.write_text(str(last))
        setval("silver_clean", "offset", last)

        # flush any leftover rows every cycle
        if batch:
            any_row = batch[-1]
            write_parquet_partition(
                batch,
                args.silver_dir,
                any_row["created_at"],
                any_row["source"],
                any_row["lang"],
            )
            batch.clear()


if __name__ == "__main__":
    main()
