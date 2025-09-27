import argparse, json, time, datetime
from pathlib import Path


def simple_sentiment(text):
    neg_words = ["poor", "bad", "كرهت", "سيئ", "terrible"]
    if any(w in text for w in neg_words):
        return "negative", 0.8, 0.1, 0.1
    if "love" in text or "ممتاز" in text:
        return "positive", 0.1, 0.1, 0.8
    return "neutral", 0.2, 0.6, 0.2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", default="silver/social.clean.jsonl")
    ap.add_argument("--scored", default="serving/social.scored.jsonl")
    ap.add_argument("--offset", default="serving/social.clean.jsonl")
    ap.add_argument("--poll", type=float, default=2.0)
    args = ap.parse_args()

    offset_file = Path(args.offset + ".offset.scored")
    last_offset = int(offset_file.read_text()) if offset_file.exists() else 0

    while True:
        lines = Path(args.clean).read_text(encoding="utf-8").splitlines()
        new_lines = lines[last_offset:]
        if not new_lines:
            time.sleep(args.poll)
            continue

        with open(args.scored, "a", encoding="utf-8") as f_out:
            for line in new_lines:
                row = json.loads(line)
                sent, pn, pneu, pp = simple_sentiment(row["clean_text"])
                scored = {
                    "post_id": row["post_id"],
                    "sentiment": sent,
                    "prob_neg": pn,
                    "prob_neu": pneu,
                    "prob_pos": pp,
                    "model_version": "sa-demo-v1",
                    "scored_at": datetime.datetime.utcnow().isoformat(),
                }
                f_out.write(json.dumps(scored) + "\n")
                print("Scored:", row["post_id"])

        last_offset += len(new_lines)
        offset_file.write_text(str(last_offset))


if __name__ == "__main__":
    main()
