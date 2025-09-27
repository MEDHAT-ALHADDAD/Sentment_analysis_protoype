# scripts/utils_text.py
import re, hashlib, math
from typing import Tuple, List

# Optional Arabic normalization via camel_tools (fallback to regex if not installed)
try:
    from camel_tools.utils.normalize import (
        normalize_alef_maksura_ar,
        normalize_alef_ar,
        normalize_teh_marbuta_ar,
    )

    CAMEL_OK = True
except Exception:
    CAMEL_OK = False

AR_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u06D6-\u06ED]")
AR_TATWEEL = re.compile(r"\u0640")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}")
URL_RE = re.compile(r"(https?://\S+|www\.\S+)")
MENTION_RE = re.compile(r"@\w+")
WS_RE = re.compile(r"\s+")


def has_arabic(text: str) -> bool:
    return any(
        "\u0600" <= ch <= "\u06ff" or "\u0750" <= ch <= "\u077f" for ch in text or ""
    )


def normalize_ar(text: str) -> str:
    t = AR_TATWEEL.sub("", text)
    t = AR_DIACRITICS.sub("", t)
    if CAMEL_OK:
        t = normalize_alef_ar(t)
        t = normalize_alef_maksura_ar(t)
        t = normalize_teh_marbuta_ar(t)
    else:
        t = (
            t.replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("ى", "ي")
            .replace("ة", "ه")
        )
    return t


def clean_text(raw: str) -> Tuple[str, bool, int, int, int]:
    """Returns (clean_text, pii_found, emoji_cnt, url_cnt, pii_items)"""
    if not raw:
        return "", False, 0, 0, 0
    email_count = len(EMAIL_RE.findall(raw))
    phone_count = len(PHONE_RE.findall(raw))
    url_count = len(URL_RE.findall(raw))
    pii_found = (email_count + phone_count) > 0

    t = EMAIL_RE.sub("<EMAIL>", raw)
    t = PHONE_RE.sub("<PHONE>", t)
    t = URL_RE.sub("<URL>", t)
    t = MENTION_RE.sub("<USER>", t)
    if has_arabic(t):
        t = normalize_ar(t)
    t = WS_RE.sub(" ", t).strip().lower()
    emoji_cnt = sum(1 for ch in t if ord(ch) > 10000)
    return t, pii_found, emoji_cnt, url_count, (email_count + phone_count)


# lang detect: heuristic first, fallback to langdetect if installed
def lang_detect(clean_text: str, hint: str | None = None) -> str:
    if has_arabic(clean_text):
        return "ar"
    try:
        from langdetect import detect

        return detect(clean_text)[:2] if clean_text else (hint or "en")
    except Exception:
        return hint if hint in ("ar", "en") else "en"


def tokenize(text: str) -> List[str]:
    return re.findall(r"<[A-Z]+>|[\w']+", text)


def hashing_vector(tokens: List[str], dim: int = 128) -> List[float]:
    v = [0.0] * dim
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        v[h % dim] += 1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]
