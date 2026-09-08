# -*- coding: utf-8 -*-
"""Neutrale Text-/Topic-Hilfen ohne Wort-, Themen- oder Suffixfilter."""


def normalize_topic_from_question(question):
    q = (question or "").strip().strip("?!.")
    low = q.lower()
    for prefix in ("was ist ", "wer ist ", "was sind ", "wer sind ", "was bedeutet "):
        if low.startswith(prefix):
            return q[len(prefix):].strip().strip("?!.").lower()
    return low


def is_good_topic(term):
    return bool((term or "").strip())


def is_good_topic_phrase(phrase):
    return bool((phrase or "").strip())


def topic_to_question(topic):
    return "Was ist " + (topic or "").strip().lower() + "?"


def clean_wikipedia_text(text):
    return "\n".join(line for line in (text or "").splitlines() if line.strip())
