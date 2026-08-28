"""NVIDIA NIM client — streaming LLM responses.

Uses the OpenAI-compatible API endpoint.
Model: deepseek-ai/deepseek-v4-pro-0813 (primary)
Fallback: meta/llama-3.2-11b-vision-instruct
"""

import httpx
import json
import structlog
from typing import AsyncGenerator

logger = structlog.get_logger()

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL = "deepseek-ai/deepseek-v4-pro-0813"
NIM_FALLBACK_MODELS = [
    "meta/llama-3.2-11b-vision-instruct",
]


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

        Tries the primary model first; if it fails (EOL, 404, 410),
        falls back to alternate models automatically.
        """
        models_to_try = [NIM_MODEL, *NIM_FALLBACK_MODELS]

        for model in models_to_try:
            success = False
            async for chunk in self._stream_with_model(
                model, messages, temperature, max_tokens
            ):
                if chunk is _RETRY_SENTINEL:
                    # This model failed with a retryable error, try next
                    break
                success = True
                yield chunk

            if success:
                return

        # All models failed
        yield "Sorry — I couldn't connect to the AI service. All available models are unavailable."

    async def _stream_with_model(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str | object, None]:
        """Attempt to stream from a specific model.

        Yields text chunks on success, or _RETRY_SENTINEL if the model
        is unavailable and we should try the next fallback.
        """
        payload = {
            "model": model,
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
                    if response.status_code in (404, 410, 503):
                        # Model unavailable — try fallback
                        error_text = await response.aread()
                        logger.warning(
                            "nim_model_unavailable",
                            model=model,
                            status=response.status_code,
                            body=error_text[:200],
                        )
                        yield _RETRY_SENTINEL
                        return

                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(
                            "nim_api_error",
                            model=model,
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
                logger.warning("nim_model_timeout", model=model)
                yield _RETRY_SENTINEL
            except Exception as e:
                logger.error("nim_stream_error", model=model, error=str(e))
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


# Sentinel object used internally to signal "try the next model"
_RETRY_SENTINEL = object()
