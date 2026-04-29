"""Embedding service — singleton wrapper around sentence-transformers model."""

from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    """Lazy-loaded sentence-transformers model for text → vector conversion."""

    def __init__(self):
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            print(f"[EmbeddingService] Loading model: {settings.EMBEDDING_MODEL}")
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            print(f"[EmbeddingService] Model loaded.")
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Single text → normalized vector."""
        vec = self.model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Batch embed for movie ingestion."""
        vecs = self.model.encode(texts, normalize_embeddings=True, batch_size=batch_size)
        return vecs.tolist()


# Singleton — reuse across the app
embedding_service = EmbeddingService()
