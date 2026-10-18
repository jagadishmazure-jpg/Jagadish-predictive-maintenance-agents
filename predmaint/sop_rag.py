"""TF-IDF retrieval over the 4 SOP documents.

Returns `file section` citations; says so explicitly when nothing matches.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

SOP_DIR = Path(__file__).resolve().parent.parent / "docs" / "sops"
MIN_SCORE = 0.08


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{3,}", text.lower())


def _load_chunks() -> list[dict]:
    chunks = []
    for path in sorted(SOP_DIR.glob("*.md")):
        section = None
        buf: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                if buf and section:
                    chunks.append({"file": path.name, "section": section,
                                   "text": "\n".join(buf)})
                section = line[3:].strip()
                buf = []
            elif line.strip():
                buf.append(line.strip())
        if buf and section and len(" ".join(buf).split()) > 4:
            chunks.append({"file": path.name, "section": section,
                           "text": "\n".join(buf)})
    return chunks


def _idf(chunks: list[dict]) -> dict[str, float]:
    df: dict[str, int] = {}
    for c in chunks:
        for tok in set(_tokens(c["text"])):
            df[tok] = df.get(tok, 0) + 1
    n = len(chunks)
    return {t: math.log(1 + n / d) for t, d in df.items()}


def retrieve(question: str, top_k: int = 2) -> dict:
    """Retrieve SOP chunks; explicit not-found when nothing scores."""
    chunks = _load_chunks()
    if not chunks:
        return {"hits": [], "found": False, "reason": "no SOP documents indexed"}
    idf = _idf(chunks)
    qt = _tokens(question)
    scored = []
    for c in chunks:
        ct = _tokens(c["text"])
        score = sum(idf.get(t, 0.0) for t in set(qt) & set(ct))
        norm = math.sqrt(len(ct)) or 1.0
        scored.append((score / norm, c))
    scored.sort(key=lambda s: s[0], reverse=True)
    hits = [
        {"file": c["file"], "section": c["section"],
         "citation": f"{c['file']} §{c['section']}",
         "excerpt": c["text"][:220]}
        for s, c in scored[:top_k] if s >= MIN_SCORE
    ]
    if not hits:
        return {"hits": [], "found": False,
                "reason": "no SOP section matched the question"}
    return {"hits": hits, "found": True}
