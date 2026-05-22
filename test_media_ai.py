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
        print(f"Media download test PASSED: {path}")
        # Verify content hash filename
        expected_hash = hashlib.sha256(b"fake image data").hexdigest()
        assert expected_hash in path
        os.remove(path)
    else:
        print("Media download test FAILED")

@patch('app.requests.post')
def test_multimodal_ai(mock_post):
    AIConfig.GEMINI_API_KEY = str("dummy")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'candidates': [{'content': {'parts': [{'text': 'Multimodal Analysis Success'}]}}]
    }
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    # Create a dummy image file
    dummy_path = "media_archive/dummy.jpg"
    with open(dummy_path, "wb") as f:
        f.write(b"dummy image data")

    ads = [{"text": "Buy now", "local_path": dummy_path}]
    result = analyze_ads_with_ai(ads)

    assert result == "Multimodal Analysis Success"
    print("Multimodal AI test PASSED")
    os.remove(dummy_path)

if __name__ == "__main__":
    test_media_download()
    test_multimodal_ai()
