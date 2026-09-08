# -*- coding: utf-8 -*-
import html
import math
import re
from collections import Counter


def strip_html(text):
    text = html.unescape(text or "")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text):
    """Alle technisch erkannten Tokens durchreichen; keine Wortfilter."""
    return re.findall(r"[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9-]*", (text or "").lower())


def counter(text):
    return Counter(tokenize(text))


def cosine(a, b):
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def sentences(text):
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if p.strip()]


def sentence_score(sentence, query_counter):
    return cosine(counter(sentence), query_counter)
