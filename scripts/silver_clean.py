import argparse, json, time, hashlib
from pathlib import Path
from utils_text import clean_text, lang_detect


def process(rec):
    clean, pii, emoji_cnt, url_cnt, _ = clean_text(rec.get("text"))
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
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="bronze/social.raw.jsonl")
    ap.add_argument("--clean", default="silver/social.clean.jsonl")
    ap.add_argument("--poll", type=float, default=2.0)
    args = ap.parse_args()

    seen = set()
    offset_file = Path(args.raw + ".offset")
    last_offset = int(offset_file.read_text()) if offset_file.exists() else 0

    while True:
        lines = Path(args.raw).read_text(encoding="utf-8").splitlines()
        new_lines = lines[last_offset:]
        if not new_lines:
            time.sleep(args.poll)
            continue

        with open(args.clean, "a", encoding="utf-8") as f_out:
            for line in new_lines:
                rec = json.loads(line)
                key = (rec.get("text", ""), rec.get("source", ""))
                if key in seen:
                    continue
                seen.add(key)
                out = process(rec)
                f_out.write(json.dumps(out, ensure_ascii=False) + "\n")
                print("Cleaned:", out["post_id"])

        last_offset += len(new_lines)
        offset_file.write_text(str(last_offset))


if __name__ == "__main__":
    main()
