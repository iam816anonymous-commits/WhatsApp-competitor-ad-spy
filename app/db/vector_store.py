import logging
import numpy as np
from typing import List, Dict, Any
from app.db.database import get_session
from app.models.models import ExtractedAd

logger = logging.getLogger("AdSpyAgent.VectorStore")

class VectorStore:
    @staticmethod
    def find_similar_creatives(embedding: bytes, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Similarity Search Interface.
        Current: Manual Cosine Similarity (Fallback)
        Future: pgvector or Qdrant
        """
        session = get_session()
        query_vec = np.frombuffer(embedding, dtype=np.float32)

        all_ads = session.query(ExtractedAd).filter(ExtractedAd.creative_embedding != None).all()
        results = []

        for ad in all_ads:
            ad_vec = np.frombuffer(ad.creative_embedding, dtype=np.float32)
            # Simple Cosine Similarity
            similarity = np.dot(query_vec, ad_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(ad_vec))
            if similarity > 0.9: # High threshold for clone detection
                 results.append({
                     "ad_id": ad.id,
                     "brand": ad.brand.name if ad.brand else "Unknown",
                     "similarity": float(similarity)
                 })

        session.close()
        return sorted(results, key=lambda x: x['similarity'], reverse=True)[:limit]
