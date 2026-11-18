import re

import jiwer


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[#*_`|>•●▪]", " ", text)  # markdown and bullet symbols
    text = re.sub(r"^\s*-{3,}\s*$", " ", text, flags=re.M)  # page separators
    return re.sub(r"\s+", " ", text).strip()


def cer(reference: str, output: str) -> float:
    return jiwer.cer(normalize(reference), normalize(output))


def wer(reference: str, output: str) -> float:
    return jiwer.wer(normalize(reference), normalize(output))


def headings_found(titles: list[str], output: str) -> int:
    """How many of the page's main headings appear in the output text."""
    text = normalize(output)
    return sum(1 for t in titles if normalize(t) and normalize(t) in text)
