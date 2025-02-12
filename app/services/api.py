
import asyncio
from contextlib import asynccontextmanager
import openai # type: ignore
from app.utils.logger import setup_logger

logger = setup_logger("api_api", "api.log")

class APIHandler:
    """Handles API calls with retry logic and error handling"""

    @asynccontextmanager
    async def api_call(self, operation: str):
        max_retries = 1
        retry_count = 0

        while retry_count < max_retries:
            try:
                yield
                break
            except openai.error.RateLimitError:
                wait_time = (retry_count + 1) * 2
                logger.warning(f"{operation} rate limited. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                retry_count += 1
            except openai.error.APIError as e:
                logger.error(f"{operation} API error: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in {operation}: {str(e)}")
                raise