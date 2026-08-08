"""Chat API router — streaming SSE endpoint."""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from cortex.chat.application.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

_service = ChatService()


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
async def create_session(job_id: str) -> SessionResponse:
    session = await _service.create_session(job_id)
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
async def stream_chat(request: ChatRequest) -> StreamingResponse:
    """Stream chat response using SSE."""

    session = await _service.get_or_create_session(
        request.job_id, request.session_id
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
async def get_history(session_id: str) -> dict:
    session = await _service.get_session(session_id)
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