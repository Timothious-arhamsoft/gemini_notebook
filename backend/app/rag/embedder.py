import logging
import time
from typing import Any, Dict, List, Tuple

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"


class BGEEmbedder:
    """
    Singleton embedder for BAAI/bge-small-en-v1.5 (384-dim vectors).
    Loads model lazily on first call to save startup time.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> Tuple[SentenceTransformer, float]:
        """Return model instance and model-load duration for this call (0 if already loaded)."""
        if self._model is not None:
            return self._model, 0.0

        logger.info(f"Loading SentenceTransformer model '{self.model_name}'...")
        load_started = time.perf_counter()
        self._model = SentenceTransformer(self.model_name)
        load_seconds = time.perf_counter() - load_started
        logger.info("SentenceTransformer model loaded successfully in %.2fs.", load_seconds)
        return self._model, load_seconds

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        vectors, _meta = self.generate_embeddings_with_metrics(texts)
        return vectors

    def generate_embeddings_with_metrics(
        self, texts: List[str]
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """
        Generate 384-dimensional embeddings for a list of text strings.

        Returns vectors and metrics (model load time, encode time, chunk count).
        """
        if not texts:
            return [], {"chunk_count": 0, "model_load_s": 0.0, "encode_s": 0.0}

        model, model_load_s = self._get_model()
        encode_started = time.perf_counter()
        # Batch encode all chunks in one call (SentenceTransformer handles micro-batches).
        embeddings = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        encode_s = time.perf_counter() - encode_started

        vectors = [emp.tolist() for emp in embeddings]
        metrics = {
            "chunk_count": len(texts),
            "model_load_s": round(model_load_s, 3),
            "encode_s": round(encode_s, 3),
        }
        return vectors, metrics


bge_embedder = BGEEmbedder()
