from fastapi import FastAPI
from app.logging_config import logger
from app.api.dev import router as dev_router
from app.api.xpost import router as xpost_router
from app.api.agent import router as agent_router
from app.scheduler import start_scheduler, stop_scheduler

app = FastAPI(title="CODEBLOODED")
app.include_router(dev_router)
app.include_router(xpost_router)
app.include_router(agent_router)

@app.on_event("startup")
async def startup_event():
    logger.info("CODEBLOODED application starting up...")
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("CODEBLOODED application shutting down...")
    stop_scheduler()

from fastapi.responses import RedirectResponse

@app.get("/")
def read_root():
    return RedirectResponse(url="/dev")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "CODEBLOODED"
    }
