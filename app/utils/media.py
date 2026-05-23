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

async def download_media(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        first_url = url.split(',')[0].strip()
        if not first_url.startswith('http'):
            return None

        async with aiohttp.ClientSession() as session:
            async with session.get(first_url, timeout=10) as response:
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

                    async def write_file():
                        with open(filepath, "wb") as f:
                            f.write(content)
                    await asyncio.to_thread(write_file)
                    return filepath
    except Exception as e:
        logger.error(f"Media download failed: {e}")
    return None

async def resolve_redirects(url: str) -> str:
    if not url or not url.startswith('http'):
        return url
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.head(url, allow_redirects=True, timeout=10) as resp:
                return str(resp.url)
    except Exception as e:
        logger.error(f"URL Resolution failed for {url}: {e}")
        return url
