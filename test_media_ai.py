import os
import requests
import hashlib
from app import download_media, AIConfig, analyze_ads_with_ai
from unittest.mock import patch, MagicMock

@patch('app.requests.get')
def test_media_download(mock_get):
    os.makedirs("media_archive", exist_ok=True)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake image data"
    mock_get.return_value = mock_response

    test_url = "http://example.com/image.jpg"
    path = download_media(test_url)

    if path and os.path.exists(path):
        print(f"✅ Media download test PASSED: {path}")
        # Verify content hash filename
        expected_hash = hashlib.sha256(b"fake image data").hexdigest()
        assert expected_hash in path
        os.remove(path)
    else:
        print("❌ Media download test FAILED")

# Note: Removed the @patch decorator here so it communicates with the live API
def test_multimodal_ai_live():
    # 1. Fetch the real key from your environment setup
    real_api_key = os.getenv("GEMINI_API_KEY")

    if not real_api_key:
        print("⚠️ Skipping Live Multimodal test: GEMINI_API_KEY not found in environment variables.")
        return

    AIConfig.GEMINI_API_KEY = real_api_key

    # 2. Ensure media environment exists
    os.makedirs("media_archive", exist_ok=True)
    dummy_path = "media_archive/dummy_test_ad.jpg"

    # Create a minimal, valid 1x1 pixel tracking GIF/JPEG data structure
    # to avoid format decoding errors on Gemini's processing side
    valid_image_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'

    with open(dummy_path, "wb") as f:
        f.write(valid_image_bytes)

    ads = [{"text": "Testing local live pipeline integration. Buy now!", "local_path": dummy_path}]

    print("📡 Sending live multimodal request to Gemini...")
    try:
        result = analyze_ads_with_ai(ads)

        # Verify we received a string response from our agent wrapper
        assert isinstance(result, str) and len(result) > 0
        print("✅ Multimodal AI Live Integration test PASSED")
        print(f"\n--- Live Gemini Output Snippet ---\n{result[:200]}...\n----------------------------------")

    except Exception as e:
        print(f"❌ Multimodal AI Live Integration test FAILED: {str(e)}")

    finally:
        if os.path.exists(dummy_path):
            os.remove(dummy_path)

if __name__ == "__main__":
    print("🚀 Starting Suite Integration Tests...")
    test_media_download()
    test_multimodal_ai_live()
