from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

from orion.api.v1.agent.routes import router as agent_v1_router
from orion.api.v1.knowledge.routes import router as knowledge_v1_router
from orion.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API for interacting with Orion",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response

app.include_router(agent_v1_router)
app.include_router(knowledge_v1_router)

@app.get("/")
def root():
    return {"message": "Welcome to Orion Agent API", "docs": "/docs", "openapi": "/openapi.json"}
