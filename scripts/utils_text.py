import re, hashlib, math

AR_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u06D6-\u06ED]")
AR_TATWEEL = re.compile(r"\u0640")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}")
URL_RE = re.compile(r"(https?://\S+|www\.\S+)")
MENTION_RE = re.compile(r"@\w+")
WS_RE = re.compile(r"\s+")


def has_arabic(text):
    return any("\u0600" <= ch <= "\u06ff" for ch in text)


def normalize_ar(text):
    text = AR_TATWEEL.sub("", text)
    text = AR_DIACRITICS.sub("", text)
    return text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")


def clean_text(raw):
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


def lang_detect(txt, hint=None):
    if has_arabic(txt):
        return "ar"
    return hint if hint in ("ar", "en") else "en"


def tokenize(txt):
    return re.findall(r"<[A-Z]+>|[\w']+", txt)


def hashing_vector(tokens, dim=64):
    v = [0.0] * dim
    for tok in tokens:
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        v[h % dim] += 1
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / norm, 6) for x in v]
