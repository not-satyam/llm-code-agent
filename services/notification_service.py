import httpx
import asyncio
import logging
from typing import Dict

log = logging.getLogger("uvicorn")

async def notify_evaluator(evaluation_url: str, payload: Dict):
    """
    Sends the final results to the evaluation_url with retries.
    """
    max_retries = 3
    delay = 2
    
    log.info(f"[Notify] Sending results to {evaluation_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(evaluation_url, json=payload, headers={"Content-Type": "application/json"})
                response.raise_for_status()
                
                log.info(f"[Notify] Success! Server responded {response.status_code}")
                return
                
            except httpx.HTTPStatusError as e:
                log.error(f"[Notify] HTTP Error on attempt {attempt+1}: {e.response.status_code}")
            except httpx.RequestError as e:
                log.error(f"[Notify] Network Error on attempt {attempt+1}: {e}")
                
            if attempt < max_retries - 1:
                log.info(f"[Notify] Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
    
    log.error("[Notify] Failed to notify evaluation server after all retries.")
    # We don't raise an exception, as the core work is done.