"""NVIDIA NIM client — streaming LLM responses.

Uses the OpenAI-compatible API endpoint.
Model: deepseek-ai/deepseek-v4-pro-0813 (primary)
Fallback: meta/llama-3.2-11b-vision-instruct
"""

import json
import re
from collections.abc import AsyncGenerator

import httpx
import structlog

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

    async def refine(
        self,
        draft: str,
        evidence: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 900,
    ) -> str:
        """Refine a Cortex-authored explanation WITHOUT changing its facts.

        This is the "NIM as verifier" contract: Cortex has already produced the
        explanation deterministically from repository evidence. NIM only improves
        readability and flow. It must NOT introduce files, symbols, metrics, or
        relationships that are not present in `evidence`, and must not contradict
        the draft's facts.

        On ANY failure (no key, network error, empty response) this returns the
        original `draft` unchanged — Cortex's explanation always stands on its own.
        """
        if not self._api_key:
            return draft

        system_msg = (
            "You are a technical editor refining an explanation that was produced "
            "by a deterministic code-analysis engine (Cortex) from verified "
            "repository evidence.\n\n"
            "STRICT RULES:\n"
            "- The DRAFT's facts are authoritative. Do NOT change any file path, "
            "symbol name, number, metric, or relationship.\n"
            "- Do NOT add facts, files, symbols, or claims not present in the "
            "EVIDENCE. If something seems missing, leave it out.\n"
            "- You MAY improve clarity, flow, phrasing, and structure only.\n"
            "- Preserve the section headings and their order.\n"
            "- If the draft is already clear, return it essentially unchanged.\n"
            "- Never contradict the draft."
        )
        user_msg = (
            f"## EVIDENCE (the only facts you may rely on)\n{evidence}\n\n"
            f"## DRAFT TO REFINE\n{draft}\n\n"
            "Return the refined explanation only."
        )
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        try:
            chunks: list[str] = []
            async for chunk in self.stream(
                messages, temperature=temperature, max_tokens=max_tokens
            ):
                chunks.append(chunk)
            refined = "".join(chunks).strip()
            # Guard 1: a suspiciously short or empty refinement means NIM failed
            # or produced garbage — fall back to the trustworthy Cortex draft.
            if len(refined) < max(40, len(draft) * 0.3):
                logger.warning("nim_refine_too_short_fallback", draft_len=len(draft),
                               refined_len=len(refined))
                return draft
            # Guard 2: grounding check. If NIM invented file paths or symbols
            # that appear in neither the draft nor the evidence, it is no longer
            # Cortex's grounded answer — reject it and return the draft.
            invented = _invented_entities(refined, draft + "\n" + evidence)
            if invented:
                logger.warning("nim_refine_invented_entities_fallback",
                               invented=invented[:8])
                return draft
            return refined
        except Exception as e:
            logger.warning("nim_refine_failed_fallback", error=str(e))
            return draft

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


# Matches file-path-like tokens (a/b/c.py) and dotted symbol references
# (module.Class.method) — the kinds of "facts" NIM must not invent.
_ENTITY_RE = re.compile(r"\b[\w./]+\.(?:py|ts|tsx|js|jsx|java|go|rb)\b|\b\w+(?:\.\w+){1,}\b")


def _invented_entities(refined: str, source: str) -> list[str]:
    """Return file/symbol-like tokens in `refined` that are absent from `source`.

    Used as a grounding guard: Cortex's draft + evidence define the allowed set
    of repository facts. Any file path or dotted symbol the refinement adds that
    is not traceable to that set is treated as fabrication.

    Conservative by design — it only flags path-like and dotted tokens (the
    shapes real repo facts take), not ordinary prose, to avoid false rejections.
    """
    source_l = source.lower()
    invented: list[str] = []
    seen: set[str] = set()
    for match in _ENTITY_RE.findall(refined):
        tok = match.strip(".")
        if not tok or len(tok) < 4:
            continue
        low = tok.lower()
        # Skip common English "sentence.Next" false positives and versions.
        if low[0].isdigit():
            continue
        if low in seen:
            continue
        seen.add(low)
        # Grounded if the whole token OR its final segment appears in the source.
        last = low.split(".")[-1]
        if low in source_l or (len(last) >= 4 and last in source_l):
            continue
        invented.append(tok)
    return invented
