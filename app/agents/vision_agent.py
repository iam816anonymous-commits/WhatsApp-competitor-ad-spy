import os
import logging
from sentence_transformers import SentenceTransformer
from PIL import Image
from typing import Optional
from functools import lru_cache
from app.db.database import get_session
from app.models.models import EmbeddingCache

logger = logging.getLogger("AdSpyAgent.Vision")

# Lazy loading of model to avoid overhead if not needed
_model: Optional[SentenceTransformer] = None

@lru_cache(maxsize=1000)
def get_cached_embedding_from_db(cache_key: str) -> Optional[bytes]:
    session = get_session()
    try:
        cached = session.get(EmbeddingCache, cache_key)
        return cached.vector if cached else None
    finally:
        session.close()

def get_model():
    global _model
    if _model is None:
        try:
            logger.info("Loading CLIP model for visual embeddings...")
            _model = SentenceTransformer('clip-ViT-B-32')
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
    return _model

def generate_image_embedding(image_path: str) -> Optional[bytes]:
    # 1. Local Disk/Name Cache Key
    cache_key = os.path.basename(image_path).split('.')[0]

    # 2. Check DB/LRU Cache
    cached_vec = get_cached_embedding_from_db(cache_key)
    if cached_vec:
        logger.debug(f"Cache hit for embedding: {cache_key}")
        return cached_vec

    model = get_model()
    if not model:
        return None

    try:
        img = Image.open(image_path)
        embedding = model.encode(img)
        emb_bytes = embedding.tobytes()

        # 3. Persist to DB
        session = get_session()
        try:
            new_cache = EmbeddingCache(content_hash=cache_key, vector=emb_bytes)
            session.merge(new_cache)
            session.commit()
        finally:
            session.close()

        return emb_bytes
    except Exception as e:
        logger.error(f"Failed to generate embedding for {image_path}: {e}")
        return None
