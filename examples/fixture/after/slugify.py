import re


def slugify(text, max_length=None):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if max_length is not None:
        text = text[:max_length].rstrip("-")
    return text
