import logging
from typing import List
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

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info(f"Loading SentenceTransformer model '{self.model_name}'...")
            self._model = SentenceTransformer(self.model_name)
            logger.info("SentenceTransformer model loaded successfully.")
        return self._model

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate 384-dimensional embeddings for a list of text strings.

        Args:
            texts: List of chunk text strings.

        Returns:
            List of 384-dim float vectors.
        """
        if not texts:
            return []

        model = self._get_model()
        # convert numpy float arrays to python list of floats
        embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return [emp.tolist() for emp in embeddings]


bge_embedder = BGEEmbedder()
