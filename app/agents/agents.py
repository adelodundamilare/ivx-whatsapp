import asyncio
import json
from typing import Dict
import os
from app.core.config import settings
from app.models.models import Intent
from openai import OpenAI # type: ignore


client = OpenAI(api_key=settings.OPENAI_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def extractor(requested_keys, message: str) -> Dict:
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            prompt = f"Extract the following keys: {requested_keys} from this text: '{message}' and return them in JSON format. If a value is missing, set it to None."

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a smart key-value pair extractor. Always return a JSON object with the requested keys."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            content = response.choices[0].message.content

            if not content:
                print("Content is empty")
                return {}

            if isinstance(content, dict):
                return content

            if isinstance(content, str):
                content = content.strip()

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                try:
                    content = content.replace("'", '"')
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(f"Failed to parse message {message} with type: {type(content)} as JSON")
                    raise  # Re-raise to trigger retry

        except Exception as e:
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                print(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Double the delay for next retry
            else:
                print(f"All {max_retries} attempts failed. Final error: {str(e)}")
                return {}

    return {}
