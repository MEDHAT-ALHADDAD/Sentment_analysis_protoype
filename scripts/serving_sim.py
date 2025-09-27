import argparse, csv, datetime
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
    ap.add_argument("--clean", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    outrows = []
    with open(args.clean, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sent, pn, pneu, pp = simple_sentiment(row["clean_text"])
            outrows.append(
                {
                    "post_id": row["post_id"],
                    "sentiment": sent,
                    "prob_neg": pn,
                    "prob_neu": pneu,
                    "prob_pos": pp,
                    "model_version": "sa-demo-v1",
                    "scored_at": datetime.datetime.utcnow().isoformat(),
                }
            )
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(outrows[0].keys()))
        w.writeheader()
        w.writerows(outrows)
    print("Serving scored:", len(outrows))


if __name__ == "__main__":
    main()
