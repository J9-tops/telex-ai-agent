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
from src.routers import jobs, trends, admin
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global variables
freelance_agent = None
scraper_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global freelance_agent, scraper_task

    logger.info("Starting Freelance Trends Agent...")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Initialize job scraper
    scraper = JobScraper(
        api_url=os.getenv("REMOTEOK_API_URL", "https://remoteok.com/api"),
        rate_limit=int(os.getenv("REMOTEOK_RATE_LIMIT", 60)),
    )

    # Initialize agent
    freelance_agent = FreelanceAgent(scraper=scraper)
    logger.info("Freelance agent initialized")

    # Start background job scraping
    scrape_interval = int(os.getenv("JOB_FETCH_INTERVAL_MINUTES", 30))
    scraper_task = asyncio.create_task(
        run_scheduled_scraping(scraper, interval_minutes=scrape_interval)
    )
    logger.info(f"Background scraping started (interval: {scrape_interval} minutes)")

    yield

    # Shutdown: Cancel background tasks
    if scraper_task:
        scraper_task.cancel()
        try:
            await scraper_task
        except asyncio.CancelledError:
            pass

    logger.info("Freelance Trends Agent shut down")


# Create FastAPI app
app = FastAPI(
    title="Freelance Trends Agent",
    description="AI agent tracking freelancing jobs and identifying emerging trends with A2A protocol support",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(jobs.router)
app.include_router(trends.router)
app.include_router(admin.router)


@app.post("/a2a/freelance")
async def a2a_endpoint(request: Request):
    """Main A2A endpoint for freelance trends agent"""
    try:
        # Parse request body
        body = await request.json()

        # Validate JSON-RPC request
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

        # Extract messages
        messages = []
        context_id = None
        task_id = None
        config = None

        if rpc_request.method == "message/send":
            messages = [rpc_request.params.message]
            config = rpc_request.params.configuration
        elif rpc_request.method == "execute":
            messages = rpc_request.params.messages
            context_id = rpc_request.params.contextId
            task_id = rpc_request.params.taskId

        # Process with freelance agent
        result = await freelance_agent.process_messages(
            messages=messages, context_id=context_id, task_id=task_id, config=config
        )

        # Build response
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
    return {"status": "healthy", "agent": "freelance-trends", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Freelance Trends Agent",
        "version": "1.0.0",
        "description": "AI agent tracking freelancing jobs and identifying emerging trends",
        "endpoints": {"a2a": "/a2a/freelance", "health": "/health", "docs": "/docs"},
        "capabilities": [
            "Track jobs from RemoteOK API",
            "Analyze trending skills and technologies",
            "Identify popular job roles",
            "Provide job search and statistics",
            "A2A protocol support",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 5001))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
