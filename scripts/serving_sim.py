# scripts/serving_sim.py
import argparse, json, time, datetime
from pathlib import Path
from metrics import incr, setval


def simple_sentiment(text):
    neg_words = ["poor", "bad", "كرهت", "سيئ", "terrible"]
    if any(w in text for w in neg_words):
        return "negative", 0.8, 0.1, 0.1
    if "love" in text or "ممتاز" in text:
        return "positive", 0.1, 0.1, 0.8
    return "neutral", 0.2, 0.6, 0.2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean_topic", default="topics/social.clean.jsonl")
    ap.add_argument("--scored_topic", default="topics/social.scored.jsonl")
    ap.add_argument("--poll", type=float, default=1.0)
    args = ap.parse_args()

    Path(args.scored_topic).parent.mkdir(parents=True, exist_ok=True)

    offset_file = Path(args.clean_topic + ".offset.scored")
    last = int(offset_file.read_text()) if offset_file.exists() else 0

    while True:
        lines = Path(args.clean_topic).read_text(encoding="utf-8").splitlines()
        new = lines[last:]
        if not new:
            time.sleep(args.poll)
            continue

        with open(args.scored_topic, "a", encoding="utf-8") as f_out:
            for line in new:
                row = json.loads(line)
                sent, pn, pneu, pp = simple_sentiment(row["clean_text"])
                msg = {
                    "post_id": row["post_id"],
                    "sentiment": sent,
                    "prob_neg": pn,
                    "prob_neu": pneu,
                    "prob_pos": pp,
                    "model_version": "sa-demo-v1",
                    "scored_at": datetime.datetime.utcnow().isoformat(),
                }
                f_out.write(json.dumps(msg) + "\n")
                incr("serving", "scored", 1)
                print("Scored:", row["post_id"])

        last += len(new)
        offset_file.write_text(str(last))
        setval("serving", "offset", last)


if __name__ == "__main__":
    main()
