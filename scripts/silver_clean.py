import argparse, csv, json, hashlib
from pathlib import Path
from utils_text import clean_text, lang_detect


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    seen = set()
    rows = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            clean, pii, emoji_cnt, url_cnt, _ = clean_text(rec.get("text"))
            lang = lang_detect(clean, rec.get("lang_hint"))
            key = (clean, rec.get("source", ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
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
            )
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("Silver cleaned:", len(rows), "→", args.out)


if __name__ == "__main__":
    main()
