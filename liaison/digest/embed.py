"""embed.py — sentence-transformers embedding 工具（singleton）"""
from __future__ import annotations

MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"
MODEL_CACHE = "/data/tools/models"
DIM         = 384

_model = None


def _load():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        import warnings
        warnings.filterwarnings("ignore")
        _model = SentenceTransformer(MODEL_NAME, cache_folder=MODEL_CACHE)
    return _model


def encode(text: str) -> list[float]:
    """回傳 384 維 float list，可直接存進 pgvector。"""
    model = _load()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()
