"""Hybrid retrieval over kb/*.md: BM25 (exact tokens like I-104) + a second ranker, fused with RRF."""
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from . import config

TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
RRF_K = 60


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def load_chunks(kb_dir) -> list[dict]:
    """One chunk per '###' section, prefixed with the article title so it stands alone."""
    chunks = []
    for path in sorted(Path(kb_dir).glob("*.md")):
        state = {"title": path.stem, "heading": ""}
        buf: list[str] = []

        def flush():
            body = "\n".join(buf).strip()
            buf.clear()
            if not body:
                return
            head = f"{state['title']} / {state['heading']}" if state["heading"] else state["title"]
            chunks.append({"id": f"{path.stem}#{len(chunks)}", "source": path.name,
                           "heading": head, "text": f"{head}\n{body}"})

        for line in path.read_text().splitlines():
            if line.startswith("## ") or (line.startswith("# ") and not line.startswith("##")):
                flush()
                state["title"], state["heading"] = line.lstrip("# ").strip(), ""
            elif line.startswith("### "):
                flush()
                state["heading"] = line[4:].strip()
            elif not line.startswith("*File:"):
                buf.append(line)
        flush()
    return chunks


def _make_dense(texts: list[str]):
    if config.DENSE_BACKEND == "minilm":
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        mat = model.encode(texts, normalize_embeddings=True)
        return lambda q: mat @ model.encode([q], normalize_embeddings=True)[0]
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    mat = vec.fit_transform(texts)
    return lambda q: (mat @ vec.transform([q]).T).toarray().ravel()


class HybridRetriever:
    def __init__(self, kb_dir=None):
        self.chunks = load_chunks(kb_dir or config.KB_DIR)
        texts = [c["text"] for c in self.chunks]
        self.bm25 = BM25Okapi([tokenize(t) for t in texts])
        self.dense = _make_dense(texts)

    def index_text(self) -> str:
        """Compact list of what the KB covers, shown to the classifier to judge deflectability."""
        return "\n".join(f"- {c['heading']}" for c in self.chunks)

    def search(self, query: str, k: int = 3) -> list[dict]:
        fused: dict[int, float] = {}
        for scores in (self.bm25.get_scores(tokenize(query)), self.dense(query)):
            for rank, idx in enumerate(np.argsort(-scores), 1):
                if scores[idx] <= 0:  # no signal, so no vote
                    break
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (RRF_K + rank)
        top = sorted(fused, key=fused.get, reverse=True)[:k]
        return [{**self.chunks[i], "score": round(fused[i], 5)} for i in top]
