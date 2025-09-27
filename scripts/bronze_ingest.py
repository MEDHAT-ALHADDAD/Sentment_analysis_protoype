import argparse, json, time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--topic", default="bronze/social.raw.jsonl")
    ap.add_argument("--interval", type=float, default=2.0, help="seconds between emits")
    args = ap.parse_args()

    topic = Path(args.topic)
    with open(args.input, encoding="utf-8") as f_in, open(
        topic, "a", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            rec = json.loads(line)
            f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f_out.flush()
            print("Produced to raw:", rec["post_id"])
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
