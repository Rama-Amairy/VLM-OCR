import re


def clean_markdown(text: str) -> str:
    text = text.strip()
    # Remove opening code block fences (e.g., ```markdown or ```) at the start
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
    # Remove closing code block fences (```) at the very end of the text
    text = re.sub(r"\n```\s*$", "", text)
    # Collapse three or more consecutive newlines down to a standard double newline
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
