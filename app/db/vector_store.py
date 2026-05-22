import logging
import numpy as np
from typing import List, Dict, Any
from app.db.database import get_session
from app.models.models import ExtractedAd

logger = logging.getLogger("AdSpyAgent.VectorStore")

class VectorStore:
    @staticmethod
    def search(embedding: bytes, table: str = "creative", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Unified Multi-modal Search Interface.
        Supports: creative, offer, landing_page
        """
        session = get_session()
        query_vec = np.frombuffer(embedding, dtype=np.float32)

        # In this stub, we only have embeddings for creatives in the model.
        # Future phases will add text embeddings for offers/landing pages.
        if table != "creative":
             session.close()
             return []

        all_ads = session.query(ExtractedAd).filter(ExtractedAd.creative_embedding != None).all()
        results = []

        for ad in all_ads:
            ad_vec = np.frombuffer(ad.creative_embedding, dtype=np.float32)
            # Cosine Similarity
            norm = (np.linalg.norm(query_vec) * np.linalg.norm(ad_vec))
            if norm == 0: continue
            similarity = np.dot(query_vec, ad_vec) / norm

            if similarity > 0.85: # Threshold for similarity
                 results.append({
                     "id": ad.id,
                     "brand": ad.brand.name if ad.brand else "Unknown",
                     "similarity": float(similarity),
                     "is_clone": similarity > 0.98
                 })

        session.close()
        return sorted(results, key=lambda x: x['similarity'], reverse=True)[:limit]

    @classmethod
    def find_cross_brand_reuse(cls, embedding: bytes, current_brand_id: int):
        results = cls.search(embedding, limit=10)
        return [r for r in results if r['brand_id'] != current_brand_id and r['similarity'] > 0.95]
