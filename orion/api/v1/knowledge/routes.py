import uuid
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl

from orion.agent.agent import Agent
from orion.logging import logger

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])

_knowledge = Agent().knowledge

class UploadLinksRequest(BaseModel):
    links: List[HttpUrl] = Field(..., description="List URL")

class UploadLinksResponse(BaseModel):
    skipped: List[HttpUrl] = Field(default_factory=list)
    processed: List[HttpUrl] = Field(default_factory=list)
    counts: Dict[str, int]

class QueryResponse(BaseModel):
    context: str

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "knowledge", "version": "v1"}

@router.post("/upload-link", response_model=UploadLinksResponse)
async def upload_link(payload: UploadLinksRequest):
    
    request_id = str(uuid.uuid4())
    # remove duplicate
    unique_links = list(dict.fromkeys([str(u) for u in payload.links]))

    try:
        result = _knowledge.upload_link(unique_links) 
        logger.info("Upload success", extra={"request_id": request_id})
    except ValueError as ve:
        logger.error("Upload failed", extra={"error": str(ve)})
        raise HTTPException(status_code=400, detail={"message": "Upload failed", "error": str(ve), "request_id": request_id})
    except Exception as e:
        logger.error("Upload failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail={"message": "Unexpected error", "error": str(e), "request_id": request_id})

    skipped_links = result.get("exists", [])
    processed_links = result.get("not_exists", [])

    return UploadLinksResponse(
        skipped=skipped_links,
        processed=processed_links,
        counts={
            "skipped": len(skipped_links),
            "processed": len(processed_links),
            "total_input": len(payload.links),
            "total_unique": len(unique_links),
        },
    )
