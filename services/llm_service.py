import httpx
import asyncio
import json
import logging
from typing import List, Dict

from config import get_settings

log = logging.getLogger("uvicorn")
settings = get_settings()

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GOOGLE_API_KEY}"

# The system prompt and schema, inspired by your reference
SYSTEM_PROMPT = """
You are an expert full-stack engineer. Your task is to generate a 
complete web application in a structured JSON response.

You must return a JSON object with a 'files' array.
Each object in the array must have 'path' (e.g., 'index.html', 'README.md', 'LICENSE')
and 'content' (the full string content of the file).

The response MUST include:
1.  index.html: A single, complete, responsive HTML file. Use Tailwind CSS via CDN. 
    All JavaScript MUST be inline inside <script> tags.
2.  README.md: Professional documentation (Title, Description, Usage).
3.  LICENSE: The full text of the MIT License.

Follow the user's brief exactly.
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "files": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "path": {"type": "STRING"},
                    "content": {"type": "STRING"}
                },
                "required": ["path", "content"]
            }
        }
    },
    "required": ["files"]
}

def create_llm_prompt(brief: str, round_index: int, attachment_names: List[str]) -> str:
    """Builds the final prompt text to send to the LLM."""
    
    if round_index > 1:
        prompt = (
            f"REVISION (ROUND {round_index}): Update the project based on this new brief: '{brief}'."
            f"You MUST provide the complete, new versions of all files (index.html, README.md, LICENSE)."
        )
    else:
        prompt = (
            f"NEW PROJECT (ROUND 1): Create a new project based on this brief: '{brief}'."
        )
        
    if attachment_names:
        prompt += (
            f"\nThe project directory will include these files: {', '.join(attachment_names)}."
            f" Ensure your code (e.g., in index.html) correctly references them."
        )
    
    return prompt

async def generate_code(prompt_text: str, image_parts: List[Dict]) -> Dict:
    """
    Calls the Gemini API with exponential backoff.
    """
    contents = []
    
    # Build the 'parts' array
    all_parts = []
    if image_parts:
        all_parts.extend(image_parts)
    all_parts.append({"text": prompt_text})
    
    contents.append({"parts": all_parts})

    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
            "temperature": 0.1,
        }
    }
    
    max_retries = 3
    base_delay = 5
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    GEMINI_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                json_text = result['candidates'][0]['content']['parts'][0]['text']
                
                log.info("[LLM] Successfully generated code.")
                return json.loads(json_text) # Parse the JSON string into a dict

            except httpx.HTTPStatusError as e:
                log.error(f"[LLM] HTTP Error on attempt {attempt+1}: {e.response.status_code} - {e.response.text[:200]}")
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                log.error(f"[LLM] Error parsing response on attempt {attempt+1}: {e}")
                log.error(f"[LLM] Raw response: {response.text[:500]}")
            except httpx.RequestError as e:
                log.error(f"[LLM] Network Error on attempt {attempt+1}: {e}")
            
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                log.info(f"[LLM] Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
    
    raise Exception("LLM code generation failed after all retries.")