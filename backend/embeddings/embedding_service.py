import hashlib
import math
import time
from typing import Optional
import numpy as np
from backend.core.config import settings
from backend.core.logging_config import app_logger, error_logger


class LocalEmbeddingService:
    """
    Hardware-aware local embedding service.
    Defaults to CPU execution (`intfloat/multilingual-e5-small`) so it never competes
    with Ollama for the 4 GB GPU VRAM on the RTX 3050 Laptop GPU.
    """

    def __init__(self) -> None:
        self.model_name = settings.EMBEDDING_MODEL
        self.device = settings.EMBEDDING_DEVICE
        self.cache_dir = str(settings.resolve_path(settings.MODELS_DIR))
        self._model = None
        self._is_e5 = "e5" in self.model_name.lower()
        self._dimension = 384
        self._fallback_mode = False
        self._last_error: Optional[str] = None

    def load_model(self) -> bool:
        if self._model is not None:
            return True
        try:
            from sentence_transformers import SentenceTransformer

            t0 = time.perf_counter()
            app_logger.info(
                f"Loading local embedding model '{self.model_name}' on device='{self.device}'..."
            )
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=self.cache_dir,
            )
            dim = (
                self._model.get_embedding_dimension()
                if hasattr(self._model, "get_embedding_dimension")
                else self._model.get_sentence_embedding_dimension()
            )
            if dim:
                self._dimension = dim
            elapsed = (time.perf_counter() - t0) * 1000
            app_logger.info(
                f"Loaded embedding model '{self.model_name}' (dim={self._dimension}) in {elapsed:.1f} ms"
            )
            self._fallback_mode = False
            self._last_error = None
            return True
        except Exception as e:
            self._last_error = str(e)
            error_logger.error(f"Failed to load SentenceTransformer '{self.model_name}': {e}")
            self._fallback_mode = True
            return False

    def _deterministic_local_vector(self, text: str) -> list[float]:
        """
        Pure-local deterministic character/word n-gram hashing vector fallback
        if the SentenceTransformer weights haven't been downloaded yet and internet is disconnected.
        """
        vec = np.zeros(self._dimension, dtype=np.float32)
        tokens = text.lower().split()
        if not tokens:
            tokens = [text.lower() or "empty"]
        for tok in tokens:
            # Word & character 3-gram features
            features = [tok] + [tok[i : i + 3] for i in range(max(0, len(tok) - 2))]
            for feat in features:
                h = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16)
                idx = h % self._dimension
                sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
                vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self.load_model()
        if self._model is not None and not self._fallback_mode:
            formatted = [f"passage: {t}" if self._is_e5 else t for t in texts]
            embeddings = self._model.encode(
                formatted,
                batch_size=16,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            return embeddings.tolist()
        return [self._deterministic_local_vector(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        self.load_model()
        if self._model is not None and not self._fallback_mode:
            formatted = f"query: {query}" if self._is_e5 else query
            embedding = self._model.encode(
                [formatted],
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            return embedding[0].tolist()
        return self._deterministic_local_vector(query)

    def get_status(self) -> dict:
        loaded = self._model is not None and not self._fallback_mode
        return {
            "status": "online" if loaded else ("fallback_local" if self._fallback_mode else "unloaded"),
            "provider": settings.EMBEDDING_PROVIDER,
            "model": self.model_name,
            "device": self.device,
            "dimension": self._dimension,
            "loaded": loaded,
            "error": self._last_error,
        }


embedding_service = LocalEmbeddingService()
