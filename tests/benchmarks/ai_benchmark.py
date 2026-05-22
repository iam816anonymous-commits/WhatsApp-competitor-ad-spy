import asyncio
import json
import logging
from typing import List, Dict
from app.agents.ai_agent import analyze_ads_with_ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AdSpy.Benchmark")

# Ground truth dataset: Mocked for this example
# In a real scenario, this would be a JSON file of human-verified ad analyses.
GROUND_TRUTH = [
    {
        "input": {
            "text": "Get 50% off our premium yoga mats! Limited time offer. Shop now.",
            "local_path": None
        },
        "expected": {
            "offer_type": "discount",
            "cta_type": "Shop Now",
            "discount": "50%"
        }
    }
]

async def run_benchmark():
    logger.info("Starting AI Benchmarking...")

    success_count = 0
    total = len(GROUND_TRUTH)

    for entry in GROUND_TRUTH:
        # Run the agent
        raw_res = await analyze_ads_with_ai([entry["input"]])

        try:
            # The agent returns a JSON string (ideally)
            # Find the first { and last } to extract JSON if it's wrapped in text
            start = raw_res.find("{")
            end = raw_res.rfind("}") + 1
            res_json = json.loads(raw_res[start:end])

            # Compare
            match = True
            for key, expected_val in entry["expected"].items():
                actual_val = res_json.get(key)
                if str(actual_val).lower() != str(expected_val).lower():
                    logger.warning(f"Mismatch for {key}: Expected {expected_val}, got {actual_val}")
                    match = False

            if match:
                success_count += 1

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}\nResponse: {raw_res}")

    accuracy = (success_count / total) * 100 if total > 0 else 0
    logger.info(f"Benchmark Complete. Accuracy: {accuracy}% ({success_count}/{total})")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
