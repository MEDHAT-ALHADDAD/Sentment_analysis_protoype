# scripts/bronze_ingest.py
import argparse, json, time
from pathlib import Path
from metrics import incr, setval


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--topic", default="topics/social.raw.jsonl")
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()

    topic = Path(args.topic)
    topic.parent.mkdir(parents=True, exist_ok=True)

    with open(args.input, encoding="utf-8") as f_in, open(
        topic, "a", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            rec = json.loads(line)
            f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f_out.flush()
            incr("bronze", "produced", 1)
            print("Produced raw:", rec.get("post_id"))
            time.sleep(args.interval)
    setval("bronze", "status", "done")


if __name__ == "__main__":
    main()
