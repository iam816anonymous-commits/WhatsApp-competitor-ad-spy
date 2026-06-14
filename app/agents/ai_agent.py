import os
import base64
import aiohttp
import logging
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("AdSpyAgent.AI")

class AIConfig:
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    _session: Optional[aiohttp.ClientSession] = None

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession()
        return cls._session

    @classmethod
    async def close_session(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()

async def analyze_ads_with_ai(ads_data_list: List[Dict[str, Any]]) -> str:
    if not AIConfig.GEMINI_API_KEY:
        return "AI analysis skipped: API Key not provided."

    parts = []
    text_summary = ""
    for i, ad in enumerate(ads_data_list[:5]):
        text_summary += f"Ad {i+1} Text: {ad['text']}\n"
        local_path = ad.get('local_path')
        if local_path and os.path.exists(local_path):
            try:
                with open(local_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg", # Should dynamically detect mime type in future
                            "data": img_data
                        }
                    })
            except Exception:
                pass

    prompt = """
    Analyze these ads (text, images, and destination URLs).
    Perform OCR on any text embedded in the graphics.

    You MUST return a JSON object with the following structure:
    {
        "analysis_text": "Full strategic summary...",
        "cta_type": "Shop Now/Learn More...",
        "emotion": "fear/desire/greed...",
        "offer_type": "discount/transformation/bundle...",
        "price_point": "$xx.xx",
        "discount": "xx%",
        "urgency_score": 1-10,
        "persona": "target audience description",
        "visual_style": "minimalist/aggressive/lifestyle...",
        "headline": "main headline extracted",
        "hook_type": "question/stat/story...",
        "cta_text": "exact button text",
        "brand_color": "dominant hex or name",
        "funnel_type": "DTC/VSL/Lead Magnet..."
    }

    Ads Context:
    """ + text_summary

    parts.append({"text": prompt})

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={AIConfig.GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": parts}]
        }
        session = await AIConfig.get_session()
        async with session.post(url, json=payload, timeout=45) as response:
            if response.status == 200:
                data = await response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                err_text = await response.text()
                logger.error(f"Gemini API error: {response.status} - {err_text}")
                return f"AI Analysis failed: {response.status}"
    except Exception as e:
        logger.error(f"AI Multimodal Analysis failed: {e}")
        return f"AI Analysis failed: {str(e)}"
