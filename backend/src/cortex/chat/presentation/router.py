"""Chat API router — streaming SSE endpoint."""

import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from cortex.auth.domain.entities import User
from cortex.auth.presentation.dependencies import get_current_user
from cortex.chat.application.chat_service import ChatService
from cortex.jobs.application.use_cases import JobService
from cortex.jobs.infrastructure.dependencies import job_repository
from shared.exceptions import NotFoundError
from shared.identity import resolve_identity
from shared.rate_limit_response import rate_limit_response
from shared.rate_limiters import get_chat_limiter

router = APIRouter(prefix="/chat", tags=["chat"])

_service = ChatService()


async def _verify_job_ownership(job_id: str, user: User) -> None:
    """Raise 404 if the job doesn't exist or isn't owned by this user.

    Chat is always scoped to a job the caller owns; this is the single
    gate that keeps one account from chatting against another's analysis."""
    job_service = JobService(job_repository)
    try:
        await job_service.get(job_id, owner_id=user.id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")


class ChatRequest(BaseModel):
    job_id: str
    message: str
    session_id: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    job_id: str


@router.post(
    "/session",
    response_model=SessionResponse,
    summary="Create a new chat session",
    description="Creates a chat session tied to a specific job/repo analysis.",
)
async def create_session(
    job_id: str,
    http_request: Request,
    user: User = Depends(get_current_user),
) -> SessionResponse:
    # Chat session creation shares the chat rate limiter
    identity = resolve_identity(http_request)
    limiter = get_chat_limiter()
    result = await limiter.check(identity)
    if not result.allowed:
        return rate_limit_response(result)  # type: ignore[return-value]

    # The job must exist and belong to this user.
    await _verify_job_ownership(job_id, user)

    session = await _service.create_session(job_id, user_id=user.id)
    return SessionResponse(
        session_id=session.id,
        job_id=session.job_id,
    )


@router.post(
    "/stream",
    summary="Send a message and stream the response",
    description=(
        "Sends a user message and streams the AI response using "
        "Server-Sent Events (SSE). Each chunk arrives as: "
        "data: {text}\\n\\n. Connect with EventSource in the browser."
    ),
)
async def stream_chat(
    request: ChatRequest,
    http_request: Request,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream chat response using SSE."""

    # ── Rate limit: chat messages ─────────────────────────────────────────
    identity = resolve_identity(http_request)
    limiter = get_chat_limiter()
    result = await limiter.check(identity)
    if not result.allowed:
        return rate_limit_response(result)  # type: ignore[return-value]

    # The job must exist and belong to this user before we chat against it.
    await _verify_job_ownership(request.job_id, user)

    session = await _service.get_or_create_session(
        request.job_id, request.session_id, user_id=user.id
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    async def event_generator():
        """Generate SSE events from the streaming response."""
        try:
            # Send session ID as first event
            yield f"data: {json.dumps({'type': 'session', 'session_id': session.id})}\n\n"

            # Stream response chunks
            async for chunk in _service.stream_response(
                session, request.message
            ):
                payload = json.dumps({"type": "chunk", "text": chunk})
                yield f"data: {payload}\n\n"

            # Send done event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_payload = json.dumps(
                {"type": "error", "message": str(e)}
            )
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/session/{session_id}/history",
    summary="Get chat history for a session",
)
async def get_history(
    session_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    session = await _service.get_session(session_id, owner_id=user.id)
    if not session:
        raise HTTPException(
            status_code=404, detail="Session not found"
        )
    return {
        "session_id": session.id,
        "job_id": session.job_id,
        "messages": [
            {
                "role": m.role.value,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in session.messages
        ],
    }