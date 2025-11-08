import asyncio
import time
import uuid
from datetime import datetime
from typing import List, Literal
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from orion.agent.agent import Agent
from orion.logging import logger

router = APIRouter(prefix="/v1/agent", tags=["agent"])

_agent = Agent()

class GenerateRequest(BaseModel):
    input: str = Field(..., description="Question")
    session_id: str = Field("halo", description="Session ID")
    user_id: str = Field(..., description="User identifier")

class GenerateResponse(BaseModel):
    answer: str
    session_id: str
    latency_ms: int


class HistoryEntry(BaseModel):
    user_id: str
    session_id: str
    input: str
    answer: str
    created_at: datetime | None = None


class HistoryResponse(BaseModel):
    histories: List[HistoryEntry]

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "orion-agent", "version": "v1"}

@router.post("/generate", response_model=GenerateResponse)
async def generate_response(req: Request, payload: GenerateRequest):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    try:
        answer = await asyncio.to_thread(
            _agent.generate,
            input=payload.input,
            session_id=payload.session_id,
            user_id=payload.user_id,
        )

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info("Agent success", extra={"request_id": request_id})

        return GenerateResponse(
            answer=answer,
            session_id=payload.session_id,
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error("Agent failed", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail={"message": "Agent failed", "error": str(e), "request_id": request_id})


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    user_id: str,
    session_id: str,
    order: Literal["ASC", "DESC"] = Query(
        default="DESC",
        description="Sort histories by creation time: 'ASC' for oldest first or 'DESC' for newest first.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip before returning results.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        description="Maximum number of history records to return.",
    ),
):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    try:
        histories = await asyncio.to_thread(
            _agent.get_history,
            user_id=user_id,
            session_id=session_id,
            order=order,
            offset=offset,
            limit=limit,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info("Fetch history success", extra={"request_id": request_id, "latency_ms": latency_ms})
        return HistoryResponse(histories=histories)
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error("Fetch history failed", extra={"request_id": request_id, "latency_ms": latency_ms})
        raise HTTPException(status_code=500, detail={"message": "Failed to fetch history", "error": str(e), "request_id": request_id})
