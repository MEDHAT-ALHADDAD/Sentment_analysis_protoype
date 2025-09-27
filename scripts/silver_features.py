import argparse, json, time
from pathlib import Path
from utils_text import tokenize, hashing_vector


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", default="silver/social.clean.jsonl")
    ap.add_argument("--feat", default="features/features.jsonl")
    ap.add_argument("--vec", default="features/vectors.jsonl")
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--poll", type=float, default=2.0)
    args = ap.parse_args()

    offset_file = Path(args.clean + ".offset")
    last_offset = int(offset_file.read_text()) if offset_file.exists() else 0

    while True:
        lines = Path(args.clean).read_text(encoding="utf-8").splitlines()
        new_lines = lines[last_offset:]
        if not new_lines:
            time.sleep(args.poll)
            continue

        with open(args.feat, "a", encoding="utf-8") as f_feat, open(
            args.vec, "a", encoding="utf-8"
        ) as f_vec:
            for line in new_lines:
                row = json.loads(line)
                feat = {
                    "post_id": row["post_id"],
                    "lang": row["lang"],
                    "domain": row["domain"],
                    "hour_of_day": (
                        row["created_at"][11:13] if row["created_at"] else ""
                    ),
                    "text_len": row["text_len"],
                    "emoji_cnt": row["emoji_cnt"],
                    "url_cnt": row["url_cnt"],
                }
                f_feat.write(json.dumps(feat) + "\n")

                vec = hashing_vector(tokenize(row["clean_text"]), dim=args.dim)
                f_vec.write(
                    json.dumps({"post_id": row["post_id"], "vector": vec}) + "\n"
                )

                print("Features extracted:", row["post_id"])

        last_offset += len(new_lines)
        offset_file.write_text(str(last_offset))


if __name__ == "__main__":
    main()
