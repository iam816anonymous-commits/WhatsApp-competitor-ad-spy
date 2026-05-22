import logging
from sentence_transformers import SentenceTransformer
from PIL import Image
from typing import Optional

logger = logging.getLogger("AdSpyAgent.Vision")

# Lazy loading of model to avoid overhead if not needed
_model: Optional[SentenceTransformer] = None

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
    model = get_model()
    if not model:
        return None
    try:
        img = Image.open(image_path)
        embedding = model.encode(img)
        return embedding.tobytes()
    except Exception as e:
        logger.error(f"Failed to generate embedding for {image_path}: {e}")
        return None
