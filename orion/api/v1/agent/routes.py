import time
import uuid
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from orion.agent.agent import Agent
from orion.logging import logger

router = APIRouter(prefix="/v1/agent", tags=["agent"])

_agent = Agent()

class GenerateRequest(BaseModel):
    input: str = Field(..., description="Question")
    session_id: str = Field("halo", description="Session ID")

class GenerateResponse(BaseModel):
    answer: str
    session_id: str
    latency_ms: int

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "orion-agent", "version": "v1"}

@router.post("/generate", response_model=GenerateResponse)
async def generate_response(req: Request, payload: GenerateRequest):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    try:
        answer = _agent.generate(input=payload.input, session_id=payload.session_id)

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
