from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import logging
import asyncio

from src.models.a2a import JSONRPCRequest, JSONRPCResponse
from src.services.freelance_agent import FreelanceAgent
from src.services.job_scraper import JobScraper, run_scheduled_scraping
from src.db.session import init_db, get_db
from src.routers import job, trends, admin, ai
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from src.schemas import Message, MessagePart

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

freelance_agent = None
scraper_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global freelance_agent, scraper_task

    logger.info("Starting Freelance Trends Agent...")

    init_db()
    logger.info("Database initialized")

    scraper = JobScraper(
        api_url=os.getenv("API_URL"), rate_limit=int(os.getenv("RATE_LIMIT", 60))
    )

    freelance_agent = FreelanceAgent(scraper=scraper)
    logger.info("Freelance agent initialized")

    logger.info("Performing initial job scrape...")
    try:
        initial_result = await scraper.scrape_and_store()
        logger.info(f"Initial scrape completed: {initial_result}")
    except Exception as e:
        logger.error(f"Initial scrape failed: {e}")

    scrape_interval = int(os.getenv("JOB_FETCH_INTERVAL_MINUTES", 30))
    scraper_task = asyncio.create_task(
        run_scheduled_scraping(scraper, interval_minutes=scrape_interval)
    )
    logger.info(f"Background scraping started (interval: {scrape_interval} minutes)")

    yield

    if scraper_task:
        scraper_task.cancel()
        try:
            await scraper_task
        except asyncio.CancelledError:
            pass

    logger.info("Freelance Trends Agent shut down")


app = FastAPI(
    title="Freelance Trends Agent",
    description="AI agent tracking freelancing jobs and identifying emerging trends with A2A protocol support",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(job.router)
app.include_router(trends.router)
app.include_router(admin.router)
app.include_router(ai.router)


@app.post("/a2a/freelance")
async def a2a_endpoint(request: Request):
    """Main A2A endpoint for freelance trends agent"""
    try:
        body = await request.json()
        logger.info(
            f"Received A2A request: method={body.get('method')}, id={body.get('id')}"
        )

        if body.get("jsonrpc") != "2.0" or "id" not in body:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: jsonrpc must be '2.0' and id is required",
                    },
                },
            )

        rpc_request = JSONRPCRequest(**body)

        messages = []
        context_id = None
        task_id = None
        config = None

        if rpc_request.method == "message/send":
            msg = rpc_request.params.message
            user_text = ""

            data_parts = [p for p in msg.parts if getattr(p, "kind", None) == "data"]
            if data_parts:
                last_messages = getattr(data_parts[0], "data", [])
                if len(last_messages) >= 2:
                    raw_text = last_messages[-2].get("text", "")
                    user_text = BeautifulSoup(raw_text, "html.parser").get_text(
                        strip=True
                    )

            if not user_text:
                text_parts = [
                    p for p in msg.parts if getattr(p, "kind", None) == "text"
                ]
                if text_parts:
                    user_text = getattr(text_parts[0], "text", "")

            messages = [
                Message(
                    kind=msg.kind,
                    role=msg.role,
                    parts=[MessagePart(kind="text", text=user_text)],
                    messageId=msg.messageId,
                )
            ]
            config = getattr(rpc_request.params, "configuration", None)
            logger.info(f"Processing message/send: {user_text}")

        elif rpc_request.method == "execute":
            messages = getattr(rpc_request.params, "messages", [])
            context_id = getattr(rpc_request.params, "contextId", None)
            task_id = getattr(rpc_request.params, "taskId", None)
            logger.info(
                f"Processing execute: {len(messages)} messages, contextId={context_id}"
            )

        logger.info("Calling freelance agent...")
        result = await freelance_agent.process_messages(
            messages=messages, context_id=context_id, task_id=task_id, config=config
        )
        logger.info(f"Agent processing completed: state={result.status.state}")

        response = JSONRPCResponse(id=rpc_request.id, result=result)
        return response.model_dump()

    except Exception as e:
        logger.error(f"Error in A2A endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": body.get("id") if "body" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"details": str(e)},
                },
            },
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from src.db.repository import JobRepository
    from src.db.session import get_db_context

    try:
        with get_db_context() as db:
            total_jobs = JobRepository.get_total_jobs(db)
            jobs_24h = JobRepository.get_jobs_count_by_period(db, hours=24)
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        total_jobs = -1
        jobs_24h = -1

    return {
        "status": "healthy",
        "agent": "freelance-trends",
        "version": "1.0.0",
        "database": {
            "connected": total_jobs >= 0,
            "total_jobs": total_jobs,
            "jobs_last_24h": jobs_24h,
        },
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Freelance Trends Agent",
        "version": "1.0.0",
        "description": "AI agent tracking freelancing jobs and identifying emerging trends",
        "endpoints": {"a2a": "/a2a/freelance", "health": "/health", "docs": "/docs"},
        "capabilities": [
            "Track latest jobs ",
            "Analyze trending skills and technologies",
            "Identify popular job roles",
            "Provide job search and statistics",
            "A2A protocol support",
        ],
    }
