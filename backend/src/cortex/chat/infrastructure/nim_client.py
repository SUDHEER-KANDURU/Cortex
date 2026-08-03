"""NVIDIA NIM client — streaming LLM responses.

Uses the OpenAI-compatible API endpoint.
Model: meta/llama-3.1-70b-instruct (free tier)
"""

import httpx
import json
import structlog
from typing import AsyncGenerator

logger = structlog.get_logger()

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL = "meta/llama-3.1-70b-instruct"


class NIMClient:
    """Streams responses from NVIDIA NIM API.

    Free tier: 1000 requests/day, no credit card needed.
    Sign up at: build.nvidia.com
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def stream(
        self,
        messages: list[dict],
        temperature: float = 0.6,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens from NIM.

        Yields individual text chunks as they arrive —
        same as ChatGPT's streaming effect.
        """
        payload = {
            "model": NIM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{NIM_BASE_URL}/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(
                            "nim_api_error",
                            status=response.status_code,
                            body=error_text[:200],
                        )
                        yield "Sorry — I couldn't connect to the AI service. Check your NIM API key."
                        return

                    async for line in response.aiter_lines():
                        if not line or line == "data: [DONE]":
                            continue
                        if not line.startswith("data: "):
                            continue

                        try:
                            data = json.loads(line[6:])
                            delta = (
                                data.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue

            except httpx.TimeoutException:
                yield "\n\n[Response timed out — please try again]"
            except Exception as e:
                logger.error("nim_stream_error", error=str(e))
                yield f"\n\n[Error: {str(e)}]"

    async def is_available(self) -> bool:
        """Check if NIM API is reachable and key is valid."""
        if not self._api_key or self._api_key == "":
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{NIM_BASE_URL}/models",
                    headers=self._headers,
                )
                return resp.status_code == 200
        except Exception:
            return False
