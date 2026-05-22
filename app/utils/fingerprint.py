import cv2
import numpy as np
from PIL import Image
import imagehash
import logging

logger = logging.getLogger("AdSpyAgent.Fingerprint")

def get_creative_fingerprint(image_path: str):
    """
    Extracts pHash and dominant colors from an image.
    """
    try:
        # 1. Perceptual Hash
        img = Image.open(image_path)
        phash = str(imagehash.phash(img))

        # 2. Dominant Colors (using OpenCV)
        cv_img = cv2.imread(image_path)
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)

        # Resize for speed
        cv_img = cv2.resize(cv_img, (100, 100), interpolation=cv2.INTER_AREA)
        pixels = cv_img.reshape(-1, 3).astype(np.float32)

        # K-Means clustering for dominant color
        n_colors = 3
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        flags = cv2.KMEANS_RANDOM_CENTERS
        _, labels, centers = cv2.kmeans(pixels, n_colors, None, criteria, 10, flags)

        # Format as string for storage
        centers = centers.astype(np.int32)
        colors_hex = []
        for c in centers:
            colors_hex.append('#%02x%02x%02x' % (c[0], c[1], c[2]))

        return {
            "phash": phash,
            "dominant_colors": ",".join(colors_hex)
        }
    except Exception as e:
        logger.error(f"Fingerprinting failed for {image_path}: {e}")
        return None

if __name__ == "__main__":
    # Test stub
    import os
    # Create a dummy image for testing if none exists
    test_path = "test_fingerprint.png"
    dummy_img = np.zeros((100,100,3), dtype=np.uint8)
    cv2.imwrite(test_path, dummy_img)

    print(f"Fingerprinting result: {get_creative_fingerprint(test_path)}")
    os.remove(test_path)
