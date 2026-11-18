"""
RAG-based retrieval engine using pure-Python TF-IDF (no numpy/scikit-learn required).
Works with any Python 3.8+ installation without heavy dependencies.
"""

import json
import math
import os
import re
from collections import Counter
from pathlib import Path


def tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric, remove stopwords."""
    _stopwords = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "its", "as", "are", "was",
        "were", "be", "been", "has", "have", "had", "do", "does", "did",
        "will", "would", "can", "could", "should", "may", "might", "that",
        "this", "these", "those", "not", "no", "so", "if", "then", "than",
        "their", "they", "we", "i", "you", "he", "she", "our", "us", "s",
        "also", "about", "which", "what", "how", "when", "where", "who",
    }
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _stopwords and len(t) > 1]


class TFIDFRetrieval:
    """Lightweight pure-Python TF-IDF retrieval engine."""

    def __init__(self):
        self.chunks: list[dict] = []
        self.texts: list[str] = []
        self.tokenized: list[list[str]] = []
        self.idf: dict[str, float] = {}
        self.tf_vectors: list[dict[str, float]] = []
        self._built = False

    def _compute_tf(self, tokens: list[str]) -> dict[str, float]:
        """Compute term frequency for a document."""
        count = Counter(tokens)
        total = len(tokens) if tokens else 1
        return {term: freq / total for term, freq in count.items()}

    def _build_index(self):
        """Build TF-IDF index over all loaded documents."""
        n = len(self.tokenized)
        if n == 0:
            return

        # Compute IDF
        doc_freq: dict[str, int] = {}
        for tokens in self.tokenized:
            for term in set(tokens):
                doc_freq[term] = doc_freq.get(term, 0) + 1

        self.idf = {
            term: math.log((n + 1) / (df + 1)) + 1
            for term, df in doc_freq.items()
        }

        # Compute TF-IDF vectors
        self.tf_vectors = []
        for tokens in self.tokenized:
            tf = self._compute_tf(tokens)
            tfidf = {term: tf_val * self.idf.get(term, 1.0)
                     for term, tf_val in tf.items()}
            self.tf_vectors.append(tfidf)

        self._built = True

    def load_chunks(self, path: str):
        """Load knowledge chunks from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)
        self.texts = [chunk["text"] for chunk in self.chunks]
        self.tokenized = [tokenize(text) for text in self.texts]
        self._build_index()
        print(f"Loaded {len(self.chunks)} knowledge chunks into retrieval engine.")

    def _cosine_sim(self, vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
        """Compute cosine similarity between two TF-IDF vectors."""
        common = set(vec_a) & set(vec_b)
        if not common:
            return 0.0
        dot = sum(vec_a[t] * vec_b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def retrieve(self, query: str, top_k: int = 5, threshold: float = 0.0) -> list[dict]:
        """Retrieve the most relevant chunks for a query."""
        if not self._built or not self.chunks:
            return []

        query_tokens = tokenize(query)
        query_tf = self._compute_tf(query_tokens)
        query_vec = {term: tf_val * self.idf.get(term, 1.0)
                     for term, tf_val in query_tf.items()}

        scores = []
        for i, doc_vec in enumerate(self.tf_vectors):
            score = self._cosine_sim(query_vec, doc_vec)
            scores.append((score, i))

        scores.sort(reverse=True)
        top = scores[:top_k]

        results = []
        for score, idx in top:
            if score >= threshold:
                results.append({
                    **self.chunks[idx],
                    "relevance_score": round(score, 4),
                })
        return results

    def get_context(self, query: str, top_k: int = 5) -> str:
        """Get formatted context string for the LLM prompt."""
        results = self.retrieve(query, top_k=top_k)
        if not results:
            return "No relevant information found in the knowledge base."

        context_parts = []
        for r in results:
            source = r.get("source", "unknown").upper()
            category = r.get("category", "general")
            context_parts.append(
                f"[Source: {source} | Category: {category}]\n{r['text']}"
            )

        return "\n\n---\n\n".join(context_parts)


class RetrievalEngine(TFIDFRetrieval):
    """Main retrieval engine — wraps TFIDFRetrieval with auto-load from default path."""

    def __init__(self, chunks_path: str | None = None):
        super().__init__()
        if chunks_path and os.path.exists(chunks_path):
            self.load_chunks(chunks_path)
        else:
            default_path = Path(__file__).parent.parent / "data" / "knowledge_chunks.json"
            if default_path.exists():
                self.load_chunks(str(default_path))
            else:
                print("Warning: No knowledge chunks found. The chatbot will have limited responses.")
