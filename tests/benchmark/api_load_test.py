import asyncio
import time
import aiohttp
import logging
from statistics import median, mean

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LoadTest")

API_URL = "http://127.0.0.1:8000/scrape"
CONCURRENT_REQUESTS = 50
TOTAL_REQUESTS = 100

async def send_request(session, i):
    start = time.perf_counter()
    try:
        async with session.post(API_URL, params={"query": f"brand_{i}"}, timeout=10) as response:
            status = response.status
            await response.json()
            duration = (time.perf_counter() - start) * 1000
            return duration, status
    except Exception as e:
        logger.error(f"Request {i} failed: {e}")
        return None, 500

async def run_load_test():
    logger.info(f"Starting Load Test: {TOTAL_REQUESTS} requests, {CONCURRENT_REQUESTS} concurrent...")

    durations = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(TOTAL_REQUESTS):
            tasks.append(send_request(session, i))

            if len(tasks) >= CONCURRENT_REQUESTS:
                results = await asyncio.gather(*tasks)
                durations.extend([d for d, s in results if d is not None])
                tasks = []

        if tasks:
            results = await asyncio.gather(*tasks)
            durations.extend([d for d, s in results if d is not None])

    if durations:
        p95 = np.percentile(durations, 95)
        p99 = np.percentile(durations, 99)
        avg = mean(durations)
        logger.info(f"--- Load Test Results ---")
        logger.info(f"Avg Latency: {avg:.2f}ms")
        logger.info(f"P95 Latency: {p95:.2f}ms")
        logger.info(f"P99 Latency: {p99:.2f}ms")
        logger.info(f"Throughput: {len(durations) / (TOTAL_REQUESTS/CONCURRENT_REQUESTS):.2f} req/sec (approx batch)")
    else:
        logger.error("No successful requests recorded.")

if __name__ == "__main__":
    import numpy as np
    asyncio.run(run_load_test())
