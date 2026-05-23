import os
import asyncio
import aiohttp
import hashlib
import io
import logging
from typing import Optional
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("AdSpyAgent.Utils")

class MediaResolver:
    _instance = None

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = MediaResolver()
            cls._instance.session = aiohttp.ClientSession(headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance and cls._instance.session:
            await cls._instance.session.close()
            cls._instance = None

async def download_media(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        first_url = url.split(',')[0].strip()
        if not first_url.startswith('http'):
            return None

        resolver = await MediaResolver.get_instance()
        async with resolver.session.get(first_url, timeout=10) as response:
            if response.status == 200:
                content = await response.read()
                h = hashlib.sha256(content).hexdigest()

                # Extension detection using PIL
                try:
                    img = Image.open(io.BytesIO(content))
                    ext = img.format.lower() if img.format else "jpg"
                except Exception:
                    ext = "jpg" # Fallback

                filename = f"{h}.{ext}"
                os.makedirs("media_archive", exist_ok=True)
                filepath = os.path.join("media_archive", filename)

                def write_file(path, data):
                    with open(path, "wb") as f:
                        f.write(data)

                await asyncio.to_thread(write_file, filepath, content)
                return filepath
    except Exception as e:
        logger.error(f"Media download failed: {e}")
    return None

async def resolve_redirects(url: str) -> str:
    if not url or not url.startswith('http'):
        return url
    try:
        resolver = await MediaResolver.get_instance()
        async with resolver.session.head(url, allow_redirects=True, timeout=10) as resp:
            return str(resp.url)
    except Exception as e:
        logger.error(f"URL Resolution failed for {url}: {e}")
        return url
